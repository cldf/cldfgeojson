"""
Convert GeoTIFF for CRS EPSG:4326 to EPSG:3857 (Web Mercator).

A GeoTIFF suitable as input for this command can be obtained for example by geo-referencing an
image file using QGIS' GeoReferencer tool.

If a JPEG file is specified as output, an additional corresponding GeoJSON file (with suffix
.bounds.geojson) will be created, storing the output of rasterio's bounds command as a way to
"locate" the image on a map. The conversion to JPEG requires the gdal_translate command.
"""
import json
import shutil
import pathlib
import mimetypes
import subprocess

from clldutils.clilib import PathType
from clldutils.jsonlib import dump
from clldutils.path import TemporaryDirectory, ensure_cmd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling


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
        webtif = _to_webmercator(in_, tmp / 'web.tif')
        if fmt == 'geotiff':
            shutil.copy(webtif, out)
            return out
        cmdline = [
            ensure_cmd('gdal_translate'), '-of', 'JPEG', '--config', 'GDAL_PAM_ENABLED', 'NO']
        if scale:
            cmdline.append('-scale')
        cmdline.extend([str(webtif), str(out)])
        #
        # Generating compressed JPEG from 4-band input doesn't seem to work. Somewhat clumsily, we
        # detect this situation by running gdal_translate enabling compression and then check for
        # warnings.
        #
        pipes = subprocess.Popen(cmdline, stderr=subprocess.PIPE)
        _, err = pipes.communicate()
        if pipes.returncode != 0:  # pragma: no cover
            raise ValueError(err)
        if (b'Warning' in err) and (b'4-band JPEGs') in err:  # pragma: no cover
            if log:
                log.info('Re-running gdal_translate to accomodate 4-band input.')
            # Run gdal_translate again without compression.
            subprocess.check_call([cmd for cmd in cmdline if cmd != '-scale'])
        dump(json.loads(subprocess.check_output(['rio', 'bounds', str(webtif)])), bounds_path(out))
    return out


def _to_webmercator(in_: pathlib.Path, out: pathlib.Path) -> pathlib.Path:
    with rasterio.open(str(in_)) as src:
        dst_crs = 'EPSG:3857'
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open(str(out), 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest)
    return out
