"""
Utilities to deal with geo-referenced images in GeoTIFF format.

Functionality in this module calls rasterio's `rio` command as well as `gdal_translate`.
"""
import json
import pathlib
import subprocess

import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from clldutils.path import ensure_cmd

from .geojson import Feature


def bounds(tif: pathlib.Path) -> Feature:
    """
    Compute the bounding box of a GeoTIFF image.
    """
    return json.loads(subprocess.check_output([ensure_cmd('rio'), 'bounds', str(tif)]))


def webmercator(in_: pathlib.Path, out: pathlib.Path) -> pathlib.Path:
    """
    Re-project a GeoTIFF image to web mercator projection.

    :param in_: Path of input GeoTIFF
    :param out: Path of output GeoTIFF
    :return: Path of output GeoTIFF
    """
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


def jpeg(tif: pathlib.Path, out: pathlib.Path, scale: bool = True, log=None) -> pathlib.Path:
    """
    Convert a GeoTIFF to JPEG format.

    :param tif: Path to input GeoTIFF
    :param out: Path for output JPEG
    :param scale: See https://gdal.org/programs/gdal_translate.html#cmdoption-gdal_translate-scale
    :param log:
    :return: Path of the JPEG output
    """
    cmdline = [
        ensure_cmd('gdal_translate'), '-of', 'JPEG', '--config', 'GDAL_PAM_ENABLED', 'NO']
    if scale:
        cmdline.append('-scale')
    cmdline.extend([str(tif), str(out)])
    #
    # Generating compressed JPEG from 4-band input doesn't seem to work. Somewhat clumsily, we
    # detect this situation by running gdal_translate enabling compression and then check for
    # warnings.
    #
    pipes = subprocess.Popen(cmdline, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
    _, err = pipes.communicate()
    if pipes.returncode != 0:  # pragma: no cover
        raise ValueError(err)
    if (b'Warning' in err) and (b'4-band JPEGs') in err:  # pragma: no cover
        if log:
            log.info('Re-running gdal_translate to accomodate 4-band input.')
        # Run gdal_translate again without compression.
        subprocess.check_call([cmd for cmd in cmdline if cmd != '-scale'])
    return out
