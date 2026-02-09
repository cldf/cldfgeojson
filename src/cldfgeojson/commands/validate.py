"""
Validate speaker area geometries in a CLDF dataset.

In order to be able to use speaker areas computationally, it is important that their geometries
are valid, e.g., do not contain self-intersecting rings. This command validates the geometries of
all GeoJSON features referenced as speaker areas from the LanguageTable, and lists invalid ones,
giving the reason for the invalidity as well as an indication of whether it can be fixed, e.g. using
`cldfgeojson.create.shapely_fixed_geometry`.
"""
from clldutils.clilib import Table, add_format
from shapely.geometry import shape
from pycldf.cli_util import add_dataset, get_dataset

from cldfgeojson import MEDIA_TYPE
from cldfgeojson.util import speaker_area_shapes
from cldfgeojson.geometry import ShapelyChecker, SpherelyChecker, Status


def register(parser):
    add_dataset(parser)
    add_format(parser, 'simple')


def run(args):
    ds = get_dataset(args)
    geojsons, geojson_by_id = speaker_area_shapes(ds)
    problems = []

    def iter_invalid(shp):
        for checker in [ShapelyChecker, SpherelyChecker]:
            status = Status.from_checker(checker, shp)
            if not status.is_valid:
                yield status

    valid_features, valid_areas = 0, 0
    if 'ContributionTable' in ds and ('ContributionTable', 'Type') in ds:
        for contrib in ds.objects('ContributionTable'):
            if contrib.data['Type'] == 'feature':
                for mid in contrib.all_related('mediaReference'):
                    if mid.cldf.mediaType == MEDIA_TYPE:
                        assert contrib.id in geojson_by_id[mid.id]
                        break
                else:
                    raise ValueError('Feature in ContributionTable but not in GeoJSON: {}'.format(
                        contrib.id))
                shp, i = shape(geojson_by_id[mid.id][contrib.id]), -1
                for i, status in enumerate(iter_invalid(shp)):
                    problems.append([contrib.id, 'feature', status.reason, status.is_fixable])
                if i < 0:
                    valid_features += 1

    for lg in ds.objects('LanguageTable'):
        if lg.cldf.speakerArea in geojsons:
            shp = geojsons[lg.cldf.speakerArea][lg.cldf.id]
        elif lg.cldf.speakerArea:  # pragma: no cover
            shp = shape(lg.speaker_area_as_geojson_feature['geometry'])
        else:
            continue

        i = -1
        for i, status in enumerate(iter_invalid(shp)):
            problems.append([lg.id, lg.cldf.glottocode, status.reason, status.is_fixable])
        if i < 0:
            valid_areas += 1

    if problems:
        with Table(args, 'id', 'glottocode', 'reason', 'fixable') as t:
            t.extend(problems)
    else:
        print('{}\tvalid features\n{}\tvalid speaker areas'.format(
            valid_features, valid_areas))
