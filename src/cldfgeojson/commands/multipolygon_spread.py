"""
Compute distances between polygons mapped to the same language.

This metric provides information about the plausibility of Glottolog matches.
E.g. for an ambiguous dialect name like "Bime", in Indonesia, if all polygons were matched to the
same Glottocode, one language would have an "outlier" polygon, resulting in a high standard
deviation for the distances between polygons for this language.
"""
import typing
import itertools
import statistics

from shapely.geometry import shape, Polygon, MultiPolygon
from clldutils.clilib import Table, add_format
from pycldf.cli_util import add_dataset, get_dataset

from cldfgeojson.util import speaker_area_shapes


def spread(shp) -> typing.Tuple[float, typing.List[Polygon]]:
    dist = 0.0
    polys = list(shp.geoms)
    if len(polys) > 2:
        dist = statistics.stdev(p1.distance(p2) for p1, p2 in itertools.combinations(polys, 2))
    elif len(polys) == 2:  # pragma: no cover
        dist = polys[0].distance(polys[1])
    return dist, polys


def register(parser):
    add_dataset(parser)
    add_format(parser, default='simple')
    parser.add_argument('--threshold', type=float, default=1.0)


def run(args):
    ds = get_dataset(args)
    geojsons = speaker_area_shapes(ds, fix_geometry=True)

    with Table(args, 'ID', 'Spread', 'NPolys') as t:
        for lg in ds.objects('LanguageTable'):
            if lg.data['Glottolog_Languoid_Level'] == 'language':
                if lg.cldf.speakerArea in geojsons:
                    shp = geojsons[lg.cldf.speakerArea][lg.cldf.id]
                elif lg.cldf.speakerArea:  # pragma: no cover
                    shp = shape(lg.speaker_area_as_geojson_feature['geometry'])

                if isinstance(shp, MultiPolygon):
                    mdist, polys = spread(shp)
                    if not mdist or mdist < args.threshold:
                        continue
                    t.append((
                        lg.id,
                        mdist,
                        len(polys),
                    ))
