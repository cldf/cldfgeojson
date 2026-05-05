"""
Convert GeoTIFF for CRS EPSG:4326 to EPSG:3857 (Web Mercator).

A GeoTIFF suitable as input for this command can be obtained for example by geo-referencing an
image file using QGIS' GeoReferencer tool.

If a JPEG file is specified as output, an additional corresponding GeoJSON file (with suffix
.bounds.geojson) will be created, storing the output of rasterio's bounds command as a way to
"locate" the image on a map. The conversion to JPEG requires the gdal_translate command.
"""
from clldutils.clilib import PathType

from cldfgeojson.cli_util import to_webmercator


def register(parser):  # pylint: disable=C0116
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


def run(args):  # pylint: disable=C0116
    to_webmercator(args.geotiff, args.output, not args.no_scale, log=args.log)
