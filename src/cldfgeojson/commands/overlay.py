"""
Create an HTML page displaying a leaflet map overlaid with a given, geo-referenced image and
tools to draw GeoJSON objects on the map.
"""
import json
import pathlib
import argparse
import mimetypes
import webbrowser

from clldutils.clilib import PathType
from clldutils.misc import data_url
from clldutils.jsonlib import load
from clldutils.path import TemporaryDirectory
from mako.lookup import TemplateLookup

from .webmercator import to_webmercator, bounds_path


def register(parser):
    parser.add_argument('--test', action='store_true', default=False, help=argparse.SUPPRESS)
    parser.add_argument(
        'input',
        type=PathType(type='file'),
        help='Geo-referenced image to be overlaid, either as GeoTIFF or as JPEG with known bounds.',
    )
    parser.add_argument(
        '--out',
        type=PathType(type='file', must_exist=False),
        help='Filename for the resulting HTML file.',
        default=pathlib.Path('index.html'),
    )
    parser.add_argument(
        '--with-draw',
        help="Flag signaling whether to include controls to draw (and export) GeoJSON objects on "
             "the map",
        action='store_true',
        default=False,
    )
    parser.add_argument(
        'geojson',
        nargs='*',
        help='Additional GeoJSON layers from files to be overlaid on the map, specified by file '
             'name.',
        type=PathType(type='file'),
    )
    parser.add_argument(
        '--no-scale',
        action='store_true',
        default=False,
    )


def run(args):
    lookup = TemplateLookup(directories=[str(pathlib.Path(__file__).parent / 'templates')])

    fmt = mimetypes.guess_type(args.input.name)[0]
    if fmt == 'image/tiff':
        with TemporaryDirectory() as tmp:
            img = data_url(
                to_webmercator(args.input, tmp / 'image.jpg', scale=not args.no_scale),
                'image/jpeg')
            bounds = load(bounds_path(tmp / 'image.jpg'))
    else:
        assert fmt == 'image/jpeg'
        img = args.input
        bounds = load(bounds_path(img))
    tmpl = lookup.get_template('index.html.mako')

    html = tmpl.render(
        img=data_url(img, 'image/jpeg') if isinstance(img, pathlib.Path) else img,
        bounds=bounds['bbox'],
        geojson=json.dumps(dict({n.stem: load(n) for n in args.geojson})),
        with_draw=args.with_draw,
    )
    args.out.write_text(html, encoding='utf8')
    if not args.test:
        webbrowser.open(str(args.out))  # pragma: no cover
