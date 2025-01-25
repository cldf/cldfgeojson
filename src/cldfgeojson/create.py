"""
Functionality to create GeoJSON FeatureCollections encoding speaker area information for datasets.
"""
import typing
import warnings
import collections

from shapely.geometry import (
    shape, Polygon, MultiPolygon, GeometryCollection, LineString, MultiLineString)
from shapely import union_all, make_valid
import antimeridian
from clldutils.color import qualitative_colors
from pycldf import Dataset
from pycldf.orm import Language as pycldfLanguage

try:  # pragma: no cover
    from pyglottolog import Glottolog
    from pyglottolog.languoids import Languoid as pyglottologLanguoid
except ImportError:  # pragma: no cover
    Glottolog = type(None)
    pyglottologLanguoid = type(None)

from . import geojson

__all__ = [
    'feature_collection',
    'fixed_geometry',
    'shapely_fixed_geometry',
    'merged_geometry',
    'aggregate',
    'InvalidRingWarning',
    'correct_longitude',
]

Languoid = typing.Union[pyglottologLanguoid, pycldfLanguage]


class InvalidRingWarning(UserWarning):
    pass


def feature_collection(features: typing.List[dict], **properties) -> dict:
    """
    A helper to create GeoJSON FeatureCollection objects from a list of features.
    """
    return dict(type="FeatureCollection", features=features, properties=properties)


def correct_longitude(lon: typing.Union[int, float]) -> typing.Union[int, float]:
    """
    Coerces a geographic longitude into the -180..180 degree range.
    """
    sign = -1 if lon < 0 else 1
    if abs(lon) > 180:
        lon = lon - sign * ((abs(lon) // 360) + 1) * 360
        if lon == -180:
            lon = 180
    return lon


def shapely_fixed_geometry(feature: geojson.Feature) -> geojson.Feature:
    shp = shape(feature['geometry'])
    if not shp.is_valid:
        valid = make_valid(shp)
        if isinstance(valid, (Polygon, MultiPolygon)):
            pass
        elif isinstance(valid, GeometryCollection):
            assert isinstance(valid.geoms[0], (Polygon, MultiPolygon))
            assert all(
                isinstance(s, (LineString, MultiLineString))
                for i, s in enumerate(valid.geoms) if i > 0)
            valid = valid.geoms[0]
        else:
            raise ValueError('Cannot make sense of return value of make_valid')  # pragma: no cover
        feature['geometry'] = valid.__geo_interface__
        assert shape(feature['geometry']).is_valid
    return feature


def fixed_geometry(feature: geojson.Feature,
                   fix_longitude: bool = False,
                   fix_antimeridian: bool = False) -> geojson.Feature:
    """
    Fixes a feature's geometry in-place.

    Note: This may cut off parts of the supposed polygon.

    :param feature:
    :param fix_longitude: Flag signaling whether to adapt longitudes such that they are between \
    -180 and 180 deg. Longitudes outside of this interval are translated by multiples of 360 to \
    fall inside.
    :param fix_antimeridian:
    :return:
    """
    if feature['geometry']['type'] not in ['Polygon', 'MultiPolygon']:
        return feature  # pragma: no cover
    multi_polygon, invalid = None, False
    polys = feature['geometry']['coordinates'] if feature['geometry']['type'] == 'MultiPolygon' \
        else [feature['geometry']['coordinates']]
    for i, poly in enumerate(polys):
        rings = []
        for ring in poly:
            if fix_longitude:
                coords = []
                for lon, lat in ring:
                    flon = correct_longitude(lon)
                    if flon != lon:
                        invalid = True
                        lon = flon
                    coords.append([lon, lat])
                ring = coords
            # Some linear rings are self-intersecting. We fix these by taking the 0-distance
            # buffer around the ring instead.
            p = Polygon(ring)
            if not p.is_valid:
                invalid = True
                p = p.buffer(0)
                assert p.is_valid
                warnings.warn('fixed invalid ring', InvalidRingWarning)
            rings.append(p.__geo_interface__['coordinates'][0])
        p = shape(dict(type='Polygon', coordinates=rings))
        assert p.is_valid
        if multi_polygon is None:
            multi_polygon = shape(dict(type='MultiPolygon', coordinates=[rings]))
        else:
            multi_polygon = multi_polygon.union(p)
        assert multi_polygon.is_valid
    if invalid:  # Make sure we only fix what's broken!
        feature['geometry'] = multi_polygon.__geo_interface__
    if fix_antimeridian:
        for poly in multi_polygon.__geo_interface__['coordinates']:
            if min(c[0] for c in poly[0]) < 0 and max(c[0] for c in poly[0]) > 0:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    feature = antimeridian.fix_geojson(feature)
                break
    return feature


def merged_geometry(features: typing.Iterable[typing.Union[geojson.Feature, geojson.Geometry]],
                    buffer: typing.Union[float, None] = 0.001,
                    ) -> geojson.Geometry:
    """
    Merge the geographic structures supplied as GeoJSON Features or Geometries.

    :param features: An iterable of geographic structures.
    :param buffer: A buffer to be added to the shapes in order to make them overlap, thereby \
    removing internal boundaries when merging. Will be subtracted from the merged geometry. \
    Specify `None` to add no buffer.
    :return: The resulting Geometry object representing the merged shapes.
    """
    features = list(features)

    if len(features) == 1:
        f = features[0]
        return f.get('geometry', f)

    def get_shape(f):
        s = shape(f.get('geometry', f))
        if buffer:
            s = s.buffer(buffer)
        return s

    res = union_all([get_shape(f) for f in features])
    if buffer:
        res = res.buffer(-buffer)
    assert res.is_valid
    return res.__geo_interface__


def aggregate(shapes: typing.Iterable[typing.Tuple[str, geojson.Feature, str]],
              glottolog: typing.Union[Glottolog, Dataset],
              level: str = 'language',
              buffer: typing.Union[float, None] = 0.001,
              opacity: float = 0.8,
              ) -> typing.Tuple[
        typing.List[geojson.Feature],
        typing.List[typing.Tuple[Languoid, list, str]]]:
    """
    Aggregate features, merging based on same language of family level Glottocode.

    :param shapes: Iterable of (feature ID, GeoJSON feature, Glottocode) triples.
    :param glottolog: Glottolog data can be supplied either as `pyglottolog.Glottolog` API object \
    or as glottolog-cldf `pycldf.Dataset`.
    :param buffer: Amount of buffering to apply when merging shapes.
    :return: A pair (features, languoids)
    """
    lang2fam = {}  # Maps glottocodes of mapped languoids to top-level families.
    polys_by_code = collections.defaultdict(list)  # Aggregates polygons per mapped glottocode.

    from_glottolog_cldf = not isinstance(glottolog, Glottolog)
    if from_glottolog_cldf:
        assert isinstance(glottolog, Dataset)
        glangs = {glang.id: glang for glang in glottolog.objects('LanguageTable')}
        for row in glottolog.iter_rows(
                'ValueTable', 'parameterReference', 'languageReference', 'value'):
            glangs[row['languageReference']].data['lineage'] = row['value'].split('/')
    else:  # pragma: no cover
        glangs = {glang.id: glang for glang in glottolog.languoids()}

    for pid, feature, gc in shapes:
        glang = glangs[gc]
        # Store feature under the associated glottocode ...
        polys_by_code[gc].append((pid, feature))

        lineage = glang.data.get('lineage', []) \
            if from_glottolog_cldf else [lin[1] for lin in glang.lineage]

        if lineage:
            # ... as well as under any glottocode in the languoid's lineage.
            for fgc in lineage:
                lang2fam[fgc] = lineage[0]
                polys_by_code[fgc].append((pid, feature))
            lang2fam[glang.id] = lineage[0]
        else:
            lang2fam[glang.id] = glang.id

    def is_language(glang):
        return glang.data['Level'] == 'language' \
            if from_glottolog_cldf else glang.level == glottolog.languoid_levels.language

    language_level_glottocodes = {gc for gc, glang in glangs.items() if is_language(glang)}
    colors = dict(zip(
        [k for k, v in collections.Counter(lang2fam.values()).most_common()],
        qualitative_colors(len(lang2fam.values()))))

    languoids, features = [], []
    for gc in sorted(language_level_glottocodes.intersection(polys_by_code)
                     if level == 'language' else sorted(set(lang2fam.values()))):
        languoids.append((
            glangs[gc],
            [p[0] for p in polys_by_code[gc]],
            glangs[lang2fam[gc]].name if lang2fam[gc] != gc else None),
        )
        features.append(dict(
            type="Feature",
            properties={
                'title': glangs[gc].name,
                'fill': colors[lang2fam[gc]],
                'family': glangs[lang2fam[gc]].name if lang2fam[gc] != gc else None,
                'cldf:languageReference': gc,
                'fill-opacity': opacity},
            geometry=merged_geometry([p[1] for p in polys_by_code[gc]], buffer=buffer)))
    return features, languoids
