"""
Create an HTML page displaying a leaflet map overlaid with a given, geo-referenced image and
tools to draw GeoJSON objects on the map.

Creates page index.html + subdir leafletdraw
"""
import json
import pathlib
import mimetypes
import webbrowser

from clldutils.clilib import PathType
from clldutils.misc import data_url
from clldutils.jsonlib import load
from clldutils.path import TemporaryDirectory
from mako.lookup import TemplateLookup

from .webmercator import to_webmercator, bounds_path


def register(parser):
    """
    optional GeoJSON layer(s)
    image
    bounds
    with leaflet.draw or without? without would allow single-file result!
    """
    parser.add_argument(
        'input',
        type=PathType(type='file'),
        help='Geo-referenced image to be overlaid, either as GeoTIFF or as JPEG with known bounds.',
    )
    parser.add_argument(
        '--out',
        type=PathType(type='file', must_exist=False),
        default=pathlib.Path('index.html'),
    )
    parser.add_argument(
        '--with-draw',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        'geojson',
        nargs='*',
        help='Additional GeoJSON layers to be overlaid on the map.',
        type=PathType(type='file'),
    )


def run(args):
    lookup = TemplateLookup(directories=[str(pathlib.Path(__file__).parent / 'templates')])

    fmt = mimetypes.guess_type(args.input.name)[0]
    if fmt == 'image/tiff':
        with TemporaryDirectory() as tmp:
            img = data_url(to_webmercator(args.input, tmp / 'image.jpg'), 'image/jpeg')
            bounds = load(bounds_path(tmp / 'image.jpg'))
    else:
        assert fmt == 'image/jpeg'
        img = args.input
        bounds = load(bounds_path(img))
    tmpl = lookup.get_template('index.html.mako')

    html = tmpl.render(
        img=data_url(img, 'image/jpeg') if isinstance(img, pathlib.Path) else img,
        bounds = bounds['bbox'],
        geojson=json.dumps(dict({n.stem: load(n) for n in args.geojson})),
        with_draw=args.with_draw,
    )
    args.out.write_text(html, encoding='utf8')
    webbrowser.open(str(args.out))
