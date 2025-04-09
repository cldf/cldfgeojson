"""
Compute the distance between speaker areas for the same language from two CLDF datasets.

Distances are given in "grid units", i.e. - since input is given as WGS 84 coordinates - in degrees
Thus, near the equator, a distance of 1 would equal roughly 111km, while further away from the
equator it will be less.

We also compute absolute and relative differences in number of polygons in the geometries and
relative difference in area size.

cldfbench geojson.compare path/to/cldf1 path/to/cldf2 --format tsv | csvstat -t

You can also print the distances to the terminal using a tool like termgraph:

cldfbench geojson.compare path/to/cldf1 path/to/cldf2 --format tsv | \
sed '/^$/d' | csvcut -t -c ID,Distance | csvsort -c Distance | csvformat -E | termgraph
"""  # noqa: E501
import collections

from shapely.geometry import MultiPolygon
from clldutils.clilib import Table, add_format
from shapely.geometry import shape
from pycldf.cli_util import add_dataset, get_dataset, UrlOrPathType
from pycldf.media import MediaTable
from pycldf.ext import discovery
from tqdm import tqdm

from cldfgeojson.geojson import MEDIA_TYPE
from cldfgeojson.create import shapely_fixed_geometry


def register(parser):
    add_dataset(parser)
    parser.add_argument(
        'dataset2',
        metavar='DATASET2',
        help="Dataset locator (i.e. URL or path to a CLDF metadata file or to the data file). "
             "Resolving dataset locators like DOI URLs might require installation of third-party "
             "packages, registering such functionality using the `pycldf_dataset_resolver` "
             "entry point.",
        type=UrlOrPathType(),
    )
    add_format(parser, 'simple')


def features_by_glottocode(ds, langs):
    speaker_areas = collections.defaultdict(dict)
    for lg in langs:
        speaker_areas[lg.cldf.speakerArea][lg.id] = lg.cldf.glottocode

    features = {}
    for media in MediaTable(ds):
        if media.id in speaker_areas:
            assert media.mimetype == MEDIA_TYPE
            geojson = {
                f['properties']['cldf:languageReference']: f for f in media.read_json()['features']}
            for lid, gc in speaker_areas[media.id].items():
                features[gc] = shapely_fixed_geometry(geojson[lid])
    return features


def langs_by_glottocode(ds):
    return {
        lg.cldf.glottocode: lg for lg in ds.objects('LanguageTable')
        if lg.cldf.glottocode and lg.cldf.speakerArea}


def run(args):
    ds1 = get_dataset(args)
    ds2 = discovery.get_dataset(args.dataset2, download_dir=args.download_dir)

    langs1 = langs_by_glottocode(ds1)
    langs2 = langs_by_glottocode(ds2)
    shared = set(langs1.keys()).intersection(set(langs2.keys()))
    features1 = features_by_glottocode(ds1, [langs1[gc] for gc in shared])
    features2 = features_by_glottocode(ds2, [langs2[gc] for gc in shared])

    with Table(
            args,
            'Glottocode', 'Distance', 'NPolys_AbsDiff', 'NPolys_RelDiff', 'Area_RelDiff'
    ) as t:
        for i, gc in tqdm(enumerate(sorted(shared), start=1)):
            feature1 = features1[gc]
            shp1 = shape(feature1['geometry'])
            feature2 = features2[gc]
            shp2 = shape(feature2['geometry'])

            npolys1 = len(shp1.geoms) if isinstance(shp1, MultiPolygon) else 1
            npolys2 = len(shp2.geoms) if isinstance(shp2, MultiPolygon) else 1

            dist = shp1.distance(shp2)
            if dist > 180:
                dist = abs(dist - 360)  # pragma: no cover
            t.append((
                gc,
                dist,
                npolys2 - npolys1,
                (npolys2 - npolys1) / npolys1,
                (shp2.area - shp1.area) / shp1.area))
