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

from cldfgeojson.util import speaker_area_shapes
from cldfgeojson.geometry import ShapelyChecker, SpherelyChecker, Status


def register(parser):
    add_dataset(parser)
    add_format(parser, 'simple')


def run(args):
    ds = get_dataset(args)
    geojsons = speaker_area_shapes(ds)
    problems = []

    for lg in ds.objects('LanguageTable'):
        if lg.cldf.speakerArea in geojsons:
            shp = geojsons[lg.cldf.speakerArea][lg.cldf.id]
        elif lg.cldf.speakerArea:  # pragma: no cover
            shp = shape(lg.speaker_area_as_geojson_feature['geometry'])
        else:
            continue

        for checker in [ShapelyChecker, SpherelyChecker]:
            status = Status.from_checker(checker, shp)
            if not status.is_valid:
                problems.append([lg.id, lg.cldf.glottocode, status.reason, status.is_fixable])

    #
    # FIXME: We should look for other polygon data as well! Loop over MediaTable, look for
    # Media_Type 'application/geo+json'
    #

    if problems:
        with Table(args, 'id', 'glottocode', 'reason', 'fixable') as t:
            t.extend(problems)
