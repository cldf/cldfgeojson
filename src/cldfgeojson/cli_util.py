"""
Utilities used in cldfgeojson commands.
"""
import pathlib
import shutil
import logging
import mimetypes
from typing import Optional

from clldutils.jsonlib import dump
from clldutils.path import TemporaryDirectory

from cldfgeojson import geotiff
from .util import PathType


def bounds_path(p: pathlib.Path) -> pathlib.Path:
    """The standard name of the GeoJSON file providing the bounds of a feature collection in p."""
    return p.parent / f'{p.name}.bounds.geojson'


def to_webmercator(
        in_: PathType,
        out: PathType,
        scale: bool = True,
        log: Optional[logging.Logger] = None):
    """Project a GEO TIFF image to webmercator."""
    fmt = 'jpg' if mimetypes.guess_type(str(out))[0] == 'image/jpeg' else 'geotiff'

    with TemporaryDirectory() as tmp:
        webtif = geotiff.webmercator(in_, tmp / 'web.tif')
        if fmt == 'geotiff':
            shutil.copy(webtif, out)
            return out
        out = geotiff.jpeg(webtif, out, scale=scale, log=log)
        dump(geotiff.bounds(webtif), bounds_path(out))
    return out
