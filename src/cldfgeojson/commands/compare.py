"""
Compute the distance between speaker areas for the same language from two CLDF datasets.

Distances are given in "grid units", i.e. - since input is given as WGS 84 coordinates - in degrees
Thus, near the equator, a distance of 1 would equal roughly 111km, while further away from the
equator it will be less.

We also compute difference in number of polygons and ratios of number of polygons and areas between
two corresponding shapes.

cldfbench geojson.compare path/to/cldf1 path/to/cldf2 --format tsv | csvstat -t

You can also print the distances to the terminal using a tool like termgraph:

cldfbench geojson.compare path/to/cldf1 path/to/cldf2 --format tsv | \
sed '/^$/d' | csvcut -t -c ID,Distance | csvsort -c Distance | csvformat -E | termgraph
"""  # noqa: E501
import collections
import dataclasses

from shapely.geometry import MultiPolygon
from shapely.geometry import shape
from clldutils.clilib import Table, add_format
from pycldf.orm import Language
from pycldf import Dataset as CLDFDataset
from pycldf.cli_util import add_dataset, get_dataset, UrlOrPathType
from pycldf.media import MediaTable
from pycldf.ext import discovery
from tqdm import tqdm

from cldfgeojson.geojson import MEDIA_TYPE, Feature
from cldfgeojson.geometry import fixed_geometry


def register(parser):  # pylint: disable=C0116
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


@dataclasses.dataclass
class Dataset:
    """A CLDF dataset and its speaker area data prepared for comparison."""
    ds: CLDFDataset
    languages: dict[str, Language]
    features: dict[str, Feature] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_dataset(cls, ds):
        """Initialize with data from a CLDF dataset."""
        return cls(
            ds,
            {
                lg.cldf.glottocode: lg for lg in ds.objects('LanguageTable')
                if lg.cldf.glottocode and lg.cldf.speakerArea})

    def load_features(self, langs: set[str]):
        """Load features associated with relevant languages."""
        langs = [self.languages[gc] for gc in langs]

        speaker_areas = collections.defaultdict(dict)
        for lg in langs:
            speaker_areas[lg.cldf.speakerArea][lg.id] = lg.cldf.glottocode

        for media in MediaTable(self.ds):
            if media.id in speaker_areas:
                assert media.mimetype == MEDIA_TYPE
                geojson = {
                    f['properties']['cldf:languageReference']: f for f in
                    media.read_json()['features']}
                for lid, gc in speaker_areas[media.id].items():
                    self.features[gc] = fixed_geometry(geojson[lid])


def run(args):  # pylint: disable=C0116
    ds1 = Dataset.from_dataset(get_dataset(args))
    ds2 = Dataset.from_dataset(discovery.get_dataset(args.dataset2, download_dir=args.download_dir))
    shared = set(ds1.languages.keys()).intersection(set(ds2.languages.keys()))
    ds1.load_features(shared)
    ds2.load_features(shared)

    with Table(
        args, 'Glottocode', 'Distance', 'NPolys_Diff', 'NPolys_Ratio', 'Area_Ratio'
    ) as t:
        for gc in tqdm(sorted(shared)):
            shp1 = shape(ds1.features[gc]['geometry'])
            shp2 = shape(ds2.features[gc]['geometry'])

            npolys1 = len(shp1.geoms) if isinstance(shp1, MultiPolygon) else 1
            npolys2 = len(shp2.geoms) if isinstance(shp2, MultiPolygon) else 1

            dist = shp1.distance(shp2)
            if dist > 180:
                dist = abs(dist - 360)  # pragma: no cover
            t.append((
                gc,
                dist,
                npolys2 - npolys1,
                npolys2 / npolys1,
                shp2.area / shp1.area))
