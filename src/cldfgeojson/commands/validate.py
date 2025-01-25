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
from shapely import is_valid_reason
from pycldf.cli_util import add_dataset, get_dataset

from cldfgeojson.util import speaker_area_shapes
from cldfgeojson.create import shapely_fixed_geometry


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
        if not shp.is_valid:
            try:
                shapely_fixed_geometry(dict(type='Feature', geometry=shp.__geo_interface__))
                fixable = True
            except:  # pragma: no cover # noqa: E722
                fixable = False

            problems.append([lg.id, lg.cldf.glottocode, is_valid_reason(shp), fixable])

    if problems:
        with Table(args, 'id', 'glottocode', 'reason', 'fixable') as t:
            t.extend(problems)
