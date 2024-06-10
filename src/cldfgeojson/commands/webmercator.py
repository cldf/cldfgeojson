"""
Convert GeoTIFF for CRS EPSG:4326 to EPSG:3857 (Web Mercator).

A GeoTIFF suitable as input for this command can be obtained for example by geo-referencing an
image file using QGIS' GeoReferencer tool.

If a JPEG file is specified as output, an additional corresponding GeoJSON file (with suffix
.bounds.geojson) will be created, storing the output of rasterio's bounds command as a way to
"locate" the image on a map. The conversion to JPEG requires the gdal_translate command.
"""
import shutil
import mimetypes

from clldutils.clilib import PathType
from clldutils.jsonlib import dump
from clldutils.path import TemporaryDirectory

from cldfgeojson import geotiff


def bounds_path(p):
    return p.parent / '{}.bounds.geojson'.format(p.name)


def register(parser):
    # -scale or not
    # -output GeoTIFF or JPEG + bounds
    parser.add_argument(
        '--no-scale',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        'geotiff',
        type=PathType(type='file'),
    )
    parser.add_argument(
        'output',
        type=PathType(type='file', must_exist=False)
    )


def run(args):
    to_webmercator(args.geotiff, args.output, not args.no_scale, log=args.log)


def to_webmercator(in_, out, scale=True, log=None):
    fmt = 'jpg' if mimetypes.guess_type(str(out))[0] == 'image/jpeg' else 'geotiff'

    with TemporaryDirectory() as tmp:
        webtif = geotiff.webmercator(in_, tmp / 'web.tif')
        if fmt == 'geotiff':
            shutil.copy(webtif, out)
            return out
        out = geotiff.jpeg(webtif, out, scale=scale, log=log)
        dump(geotiff.bounds(webtif), bounds_path(out))
    return out
