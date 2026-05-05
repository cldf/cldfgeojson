"""
Validate speaker area geometries in a CLDF dataset.

In order to be able to use speaker areas computationally, it is important that their geometries
are valid, e.g., do not contain self-intersecting rings. This command validates the geometries of
all GeoJSON features referenced as speaker areas from the LanguageTable, and lists invalid ones,
giving the reason for the invalidity as well as an indication of whether it can be fixed, e.g. using
`cldfgeojson.create.shapely_fixed_geometry`.
"""
import dataclasses
from collections.abc import Generator

from clldutils.clilib import Table, add_format
from shapely import Geometry
from shapely.geometry import shape
from pycldf.cli_util import add_dataset, get_dataset

from cldfgeojson import MEDIA_TYPE
from cldfgeojson.util import speaker_area_shapes
from cldfgeojson.geometry import ShapelyChecker, SpherelyChecker, Status


def register(parser):  # pylint: disable=C0116
    add_dataset(parser)
    add_format(parser, 'simple')


def run(args):  # pylint: disable=C0116
    ds = get_dataset(args)
    geojsons, geojson_by_id = speaker_area_shapes(ds)

    validator = Validator()
    if 'ContributionTable' in ds and ('ContributionTable', 'Type') in ds:
        for contrib in ds.objects('ContributionTable'):
            if contrib.data['Type'] == 'feature':
                for mid in contrib.all_related('mediaReference'):
                    if mid.cldf.mediaType == MEDIA_TYPE:
                        assert contrib.id in geojson_by_id[mid.id]
                        break
                else:
                    raise ValueError(
                        f'Feature in ContributionTable but not in GeoJSON: {contrib.id}')
                validator.validate(geojson_by_id[mid.id][contrib.id], contrib.id, 'feature')

    for lg in ds.objects('LanguageTable'):
        if lg.cldf.speakerArea in geojsons:
            shp = geojsons[lg.cldf.speakerArea][lg.cldf.id]
        elif lg.cldf.speakerArea:  # pragma: no cover
            shp = shape(lg.speaker_area_as_geojson_feature['geometry'])
        else:
            continue

        validator.validate(shp, lg.id, lg.cldf.glottocode)

    validator.report(args)


@dataclasses.dataclass
class Validator:
    """Validation methods together with summary stats about results."""
    problems: list[tuple[str, str, str, bool]] = dataclasses.field(default_factory=list)
    valid_features: int = 0
    valid_areas: int = 0

    @staticmethod
    def iter_invalid(shp: Geometry) -> Generator[Status, None, None]:
        """Yield failed checks."""
        for checker in [ShapelyChecker, SpherelyChecker]:
            status = Status.from_checker(checker, shp)
            if not status.is_valid:
                yield status

    def validate(self, shp: Geometry, id_: str, type_: str):
        """Validate a speaker area."""
        i = -1
        for i, status in enumerate(self.iter_invalid(shp)):
            self.problems.append((id_, type_, status.reason, status.is_fixable))
        if i < 0:
            self.valid_areas += 1

    def report(self, args):
        """Print summary stats about the validation."""
        if self.problems:
            with Table(args, 'id', 'glottocode', 'reason', 'fixable') as t:
                t.extend(self.problems)
        else:
            print(f'{self.valid_features}\tvalid features\n{self.valid_areas}\tvalid speaker areas')
