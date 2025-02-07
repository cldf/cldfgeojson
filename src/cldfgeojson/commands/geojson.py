"""
Create a GeoJSON file containing speaker area features from a dataset for selected language IDs.

This command is particularly useful to create a GeoJSON file to inspect cases of high distances
between a speaker area and the corresponding Glottolog point coordinate.
"""  # noqa: E501
import sys
import json
import itertools

from pycldf.cli_util import add_dataset, get_dataset
from clldutils.color import qualitative_colors

from cldfgeojson.util import speaker_area_shapes
from cldfgeojson.create import feature_collection


def arg_or_stdin(s):
    if s == '-':
        return sys.stdin.read().splitlines()  # pragma: no cover
    return s


def register(parser):
    add_dataset(parser)
    parser.add_argument('language_ids', type=arg_or_stdin, nargs='+')
    parser.add_argument(
        '--glottolog',
        metavar='GLOTTOLOG',
        help='Path to repository clone of Glottolog data')
    parser.add_argument(
        '--glottolog-version',
        help='Version of Glottolog data to checkout',
        default=None)


def run(args):
    lids = set(itertools.chain.from_iterable(
        obj if isinstance(obj, list) else [obj] for obj in args.language_ids))
    colors = dict(zip(lids, qualitative_colors(len(lids))))

    ds = get_dataset(args)
    geojsons = speaker_area_shapes(ds, fix_geometry=True, with_properties=True)
    if args.glottolog:
        gl = {lg.id: lg for lg in args.glottolog.api.languoids() if lg.longitude}
    else:
        gl = {}

    features = []
    for lg in ds.objects('LanguageTable'):
        if lg.id in lids:
            if lg.cldf.speakerArea in geojsons:
                shp, props = geojsons[lg.cldf.speakerArea][lg.cldf.id]
                feature = dict(type='Feature', geometry=shp.__geo_interface__, properties=props)
            elif lg.cldf.speakerArea:  # pragma: no cover
                feature = lg.speaker_area_as_geojson_feature
            else:  # pragma: no cover
                args.log.warning('No speaker area for language ID {}'.format(lg.id))
                continue
            for k, v in lg.data.items():
                if k not in {'ID', 'Name', 'Latitude', 'Longitude', 'Glottocode'}:
                    feature['properties'].setdefault(k, str(v))
            feature['properties'].update({
                'title': '{}: {}'.format(lg.id, lg.cldf.name),
                "stroke": colors[lg.id],
                "fill": colors[lg.id],
                "fill-opacity": 0.5,
            })
            features.append(feature)
            if args.glottolog:
                if lg.cldf.glottocode in gl:
                    glang = gl[lg.cldf.glottocode]
                    features.append(dict(
                        type='Feature',
                        geometry=dict(type='Point', coordinates=[glang.longitude, glang.latitude]),
                        properties={
                            'title': '{} -> {}: {}'.format(lg.id, glang.id, glang.name),
                            "marker-color": colors[lg.id]},
                    ))
                else:  # pragma: no cover
                    args.log.warning('No Glottolog coordinate for language ID {}'.format(lg.id))
    print(json.dumps(feature_collection(features), indent=2))
