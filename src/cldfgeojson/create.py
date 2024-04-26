"""
Functionality to create GeoJSON FeatureCollections encoding speaker area information for datasets.
"""
import typing
import collections

from shapely.geometry import shape, Polygon
from shapely import union_all
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

__all__ = ['feature_collection', 'fixed_geometry', 'merged_geometry', 'aggregate']

Languoid = typing.Union[pyglottologLanguoid, pycldfLanguage]


def feature_collection(features: typing.List[dict], **properties) -> dict:
    """
    A helper to create GeoJSON FeatureCollection objects from a list of features.
    """
    return dict(type="FeatureCollection", features=features, properties=properties)


def fixed_geometry(feature: geojson.Feature) -> geojson.Feature:
    """
    Note: This may cut off parts of the supposed polygon.

    :param feature:
    :return:
    """
    if feature['geometry']['type'] not in ['Polygon', 'MultiPolygon']:
        return feature  # pragma: no cover
    multi_polygon = None
    polys = feature['geometry']['coordinates'] if feature['geometry']['type'] == 'MultiPolygon' \
        else [feature['geometry']['coordinates']]
    for i, poly in enumerate(polys):
        rings = []
        for ring in poly:
            # Some linear rings are self-intersecting. We fix these by taking the 0-distance
            # buffer around the ring instead.
            p = Polygon(ring)
            if not p.is_valid:
                p = p.buffer(0)
                assert p.is_valid
            rings.append(p.__geo_interface__['coordinates'][0])
        p = shape(dict(type='Polygon', coordinates=rings))
        assert p.is_valid
        if multi_polygon is None:
            multi_polygon = shape(dict(type='MultiPolygon', coordinates=[rings]))
        else:
            multi_polygon = multi_polygon.union(p)
        assert multi_polygon.is_valid
    feature['geometry'] = multi_polygon.__geo_interface__
    return feature


def merged_geometry(features: typing.Iterable[geojson.Feature]) -> geojson.Geometry:
    # Note: We slightly increase each polygon using `buffer` to make sure they overlap a bit and
    # internal boundaries are thus removed.
    return union_all([shape(f['geometry']).buffer(0.001) for f in features])


def aggregate(shapes: typing.Iterable[typing.Tuple[str, geojson.Feature, str]],
              glottolog: typing.Union[Glottolog, Dataset],
              level: str = 'language',
              ) -> typing.Tuple[
        typing.List[geojson.Feature],
        typing.List[typing.Tuple[Languoid, list, str]]]:
    """
    :param shapes: Iterable of (feature ID, GeoJSON feature, Glottocode) triples.
    :param glottolog: Glottolog data can be supplied either as `pyglottolog.Glottolog` API object \
    or as glottolog-cldf `pycldf.Dataset`.
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
                'fill-opacity': 0.8},
            geometry=merged_geometry([p[1] for p in polys_by_code[gc]]).__geo_interface__))
    return features, languoids