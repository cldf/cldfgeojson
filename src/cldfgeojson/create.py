"""
Functionality to create GeoJSON FeatureCollections encoding speaker area information for datasets.
"""
import typing
import collections

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
from cldfgeojson.geometry import merged_geometry

__all__ = [
    'feature_collection',
    'aggregate',
]

Languoid = typing.Union[pyglottologLanguoid, pycldfLanguage]


def feature_collection(features: typing.List[dict], **properties) -> dict:
    """
    A helper to create GeoJSON FeatureCollection objects from a list of features.
    """
    return dict(type="FeatureCollection", features=features, properties=properties)


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

    def has_level(glang):
        return glang.data['Level'] == level \
            if from_glottolog_cldf else glang.level == getattr(glottolog.languoid_levels, level)

    level_glottocodes = {gc for gc, glang in glangs.items() if has_level(glang)}
    colors = dict(zip(
        [k for k, v in collections.Counter(lang2fam.values()).most_common()],
        qualitative_colors(len(lang2fam.values()))))

    languoids, features = [], []
    for gc in sorted(level_glottocodes.intersection(polys_by_code)
                     if level != 'family' else sorted(set(lang2fam.values()))):
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
