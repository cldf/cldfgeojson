"""
Functionality to create GeoJSON FeatureCollections encoding speaker area information for datasets.
"""
import dataclasses
from typing import Union, Literal
import collections
from collections.abc import Iterable

from clldutils.color import qualitative_colors
from pycldf import Dataset
from pycldf.orm import Language as pycldfLanguage

try:  # pragma: no cover
    from pyglottolog import Glottolog
    from pyglottolog.languoids import Languoid as pyglottologLanguoid
except ImportError:  # pragma: no cover
    Glottolog = type(None)
    pyglottologLanguoid = type(None)  # pylint: disable=invalid-name

from cldfgeojson.geometry import merged_geometry
from . import geojson

__all__ = [
    'feature_collection',
    'aggregate',
]

LanguoidLevelType = Literal['family', 'language', 'dialect']
Languoid = Union[pyglottologLanguoid, pycldfLanguage]


def feature_collection(features: list[geojson.Feature], **properties) -> dict:
    """
    A helper to create GeoJSON FeatureCollection objects from a list of features.
    """
    return {'type': "FeatureCollection", 'features': features, 'properties': properties}


@dataclasses.dataclass(frozen=True)
class GlottologLanguoid:
    """
    We must be able to handle Glottolog data from CLDF or the pyglottolog API. This class helps
    abstract the differences.
    """
    lg: Languoid
    level: LanguoidLevelType
    lineage: list[str] = dataclasses.field(default_factory=list)


def _get_glangs(glottolog) -> dict[str, GlottologLanguoid]:
    if isinstance(glottolog, Dataset):
        glangs = {
            glang.id: GlottologLanguoid(glang, glang.data['Level'])
            for glang in glottolog.objects('LanguageTable')}
        for row in glottolog.iter_rows(
                'ValueTable', 'parameterReference', 'languageReference', 'value'):
            glangs[row['languageReference']].lineage.extend(row['value'].split('/'))
        return glangs
    return {
        glang.id: GlottologLanguoid(glang, glang.level.name, [i[1] for i in glang.lineage])
        for glang in glottolog.languoids()}


@dataclasses.dataclass
class ShapeData:
    """Data collected from shapes suitable for aggregation."""
    gc_to_family: dict[str, str] = dataclasses.field(default_factory=dict)
    gc_to_shapes: dict[str, list[tuple[str, geojson.Feature]]] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(list))

    @classmethod
    def from_shapetriples(
            cls,
            shapes: Iterable[tuple[str, geojson.Feature, str]],
            glangs: dict[str, GlottologLanguoid],
    ) -> 'ShapeData':
        """Initialize from shape triples."""
        res = cls()
        for pid, feature, gc in shapes:
            glang = glangs[gc]
            # Store feature under the associated glottocode ...
            res.gc_to_shapes[gc].append((pid, feature))

            if glang.lineage:
                # ... as well as under any glottocode in the languoid's lineage.
                for fgc in glang.lineage:
                    res.gc_to_family[fgc] = glang.lineage[0]
                    res.gc_to_shapes[fgc].append((pid, feature))
                res.gc_to_family[glang.lg.id] = glang.lineage[0]
            else:
                res.gc_to_family[glang.lg.id] = glang.lg.id
        return res


def aggregate(
        shapes: Iterable[tuple[str, geojson.Feature, str]],
        glottolog: Union[Glottolog, Dataset],
        level: LanguoidLevelType = 'language',
        buffer: Union[float, None] = 0.001,
        opacity: float = 0.8,
) -> tuple[list[geojson.Feature], list[tuple[Languoid, list, str]]]:
    """
    Aggregate features, merging based on same language of family level Glottocode.

    :param shapes: Iterable of (feature ID, GeoJSON feature, Glottocode) triples.
    :param glottolog: Glottolog data can be supplied either as `pyglottolog.Glottolog` API object \
    or as glottolog-cldf `pycldf.Dataset`. The languoids returned will then be of the appropriate \
    type.
    :param buffer: Amount of buffering to apply when merging shapes.
    :return: A pair (features, languoids)
    """
    glangs: dict[str, GlottologLanguoid] = _get_glangs(glottolog)
    data = ShapeData.from_shapetriples(shapes, glangs)

    colors = dict(zip(
        [k for k, v in collections.Counter(data.gc_to_family.values()).most_common()],
        qualitative_colors(len(data.gc_to_family.values()))))

    languoids: list[tuple[Languoid, list, str]] = []
    features: list[geojson.Feature] = []
    for gc in sorted(
            {gc for gc, lg in glangs.items() if lg.level == level}.intersection(data.gc_to_shapes)
            if level != 'family' else sorted(set(data.gc_to_family.values()))):
        languoids.append((
            glangs[gc].lg,
            [p[0] for p in data.gc_to_shapes[gc]],
            glangs[data.gc_to_family[gc]].lg.name if data.gc_to_family[gc] != gc else None),
        )
        features.append(geojson.get_feature(
            merged_geometry([p[1] for p in data.gc_to_shapes[gc]], buffer=buffer),
            {
                'title': glangs[gc].lg.name,
                'fill': colors[data.gc_to_family[gc]],
                'family': glangs[data.gc_to_family[gc]].lg.name
                if data.gc_to_family[gc] != gc else None,
                'cldf:languageReference': gc,
                'fill-opacity': opacity}))
    return features, languoids
