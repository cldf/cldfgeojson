"""
Functionality to assess the validity of feature geometries and possibly fix invalid ones.
"""
import json
import pathlib
import random
import string
from typing import Protocol, Optional, Union
import tempfile
import warnings
from collections.abc import Iterable
import dataclasses

from shapely import (
    is_valid, is_valid_reason, make_valid, simplify, remove_repeated_points, Geometry, union_all)
from shapely.geometry import (
    shape, Polygon, MultiPolygon, GeometryCollection, LineString, MultiLineString, MultiPoint)
from shapely.ops import unary_union
import numpy as np
import antimeridian

try:
    import spherely
except ImportError:
    spherely = None

from cldfgeojson import geojson

PathType = Union[str, pathlib.Path]


def randstring(length: int = 6) -> str:
    """A random string of a certain length."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def check_feature(
        geom: Geometry,
        feature: Optional[geojson.Feature] = None,
        tdir: Optional[PathType] = None):
    """Check the validity of a geometry."""
    if not all(checker.is_valid(geom)[0] for checker in [ShapelyChecker, SpherelyChecker]):
        if feature is None:
            feature = {'properties': {'id': randstring()}, 'type': 'Feature'}
        feature['geometry'] = geojson.get_geometry(geom)
        p = pathlib.Path(tempfile.gettempdir() if tdir is None else tdir).joinpath(
            'invalid_{}.geojson'.format(feature['properties']['id']))
        p.write_text(json.dumps(feature, indent=2), encoding='utf8')
        raise ValueError(f'Invalid feature geometry written to {p}')


class InvalidRingWarning(UserWarning):
    pass


class ValidityChecker(Protocol):
    @staticmethod
    def is_valid(shp: Geometry) -> tuple[bool, str]:  # pragma: no cover
        ...

    @staticmethod
    def fixer(shp: Geometry) -> Geometry:  # pragma: no cover
        ...


@dataclasses.dataclass
class Status:
    is_valid: bool = True
    is_fixable: bool = True
    reason: str = None

    @classmethod
    def from_checker(cls, checker: ValidityChecker, shp: Geometry) -> 'Status':
        is_valid = checker.is_valid(shp)
        is_fixable = True
        if not is_valid[0]:
            try:
                checker.fixer(shp)
            except ValueError:
                is_fixable = False
        return cls(
            is_valid=is_valid[0],
            is_fixable=is_fixable,
            reason=is_valid[1])


class ShapelyChecker:
    @staticmethod
    def is_valid(shp: Geometry) -> tuple[bool, str]:
        if is_valid(shp):
            return True, ''
        return False, is_valid_reason(shp)

    @staticmethod
    def fixer(shp: Geometry) -> Geometry:
        if not is_valid(shp):
            valid = make_valid(shp)
            if isinstance(valid, (Polygon, MultiPolygon)):
                pass
            elif isinstance(valid, GeometryCollection):
                assert isinstance(valid.geoms[0], (Polygon, MultiPolygon))
                # shapely's make_valid sometimes introduces tiny polygons. We prune these.
                assert len([
                    s for s in valid.geoms
                    if isinstance(s, (Polygon, MultiPolygon)) and s.area > 1e-15]) == 1
                assert all(
                    isinstance(s, (LineString, MultiLineString, MultiPoint))
                    for i, s in enumerate(valid.geoms) if i > 0), [type(g) for g in valid.geoms]
                valid = valid.geoms[0]
            else:
                raise ValueError(
                    'Cannot make sense of return value of make_valid')  # pragma: no cover
            shp = shape(valid.__geo_interface__)
            if not is_valid(shp):
                raise ValueError('Could not make the geometry valid')  # pragma: no cover
        return shp


class SpherelyChecker:
    @staticmethod
    def is_valid(shp) -> tuple[bool, str]:
        if spherely is None:  # pragma: no cover
            return True, ''
        try:
            spherely.from_wkt(shp.wkt)
            return True, ''
        except RuntimeError as e:
            return False, str(e)

    @staticmethod
    def fixer(shp: Geometry) -> Geometry:
        if spherely is None:  # pragma: no cover
            return shp
        if not ShapelyChecker.is_valid(shp)[0]:
            raise ValueError('Cannot fix (shapely) invalid geometry')
        try:
            spherely.from_wkt(shp.wkt)
            return shp
        except RuntimeError:
            pass

        # Invalid - attempt auto-fix
        fixed_geom = remove_repeated_points(shp, 0.00001)
        fixed_geom = unary_union(fixed_geom)
        fixed_geom = fixed_geom.buffer(0.0000001)
        fixed_geom = simplify(fixed_geom, 0.000009)
        fixed_geom = fixed_geom.buffer(-0.00001).buffer(0.00001)

        # Check if fix worked
        try:
            spherely.from_wkt(fixed_geom.wkt)
            # Fixed successfully
            return fixed_geom
        except RuntimeError:
            # Still invalid - try spike removal on original planar geometry
            pass

        spike_fixed_geom = remove_spikes_from_polygon(shp)
        if spike_fixed_geom is not None:
            try:
                spherely.from_wkt(spike_fixed_geom.wkt)
                # Spike removal fixed it
                return fixed_geom
            except RuntimeError:  # pragma: no cover
                pass  # So far we haven't found a polygon that couldn't be fixed.
        raise ValueError('Could not make the polygon valid')  # pragma: no cover


def merged_geometry(
        features: Iterable[Union[geojson.Feature, geojson.Geometry]],
        buffer: Union[float, None] = 0.001,
) -> geojson.Geometry:
    """
    Merge the geographic structures supplied as GeoJSON Features or Geometries.

    :param features: An iterable of geographic structures.
    :param buffer: A buffer to be added to the shapes in order to make them overlap, thereby \
    removing internal boundaries when merging. Will be subtracted from the merged geometry. \
    Specify `None` to add no buffer.
    :return: The resulting Geometry object representing the merged shapes.
    """
    features = list(features)

    if len(features) == 1:
        f = features[0]
        return f.get('geometry', f)

    def get_shape(f):
        s = shape(f.get('geometry', f))
        if buffer:
            s = s.buffer(buffer)
        return s

    res = union_all([get_shape(f) for f in features])
    if buffer:
        res = res.buffer(-buffer)
    for fixer in ShapelyChecker, SpherelyChecker:
        res = fixer.fixer(res)
    check_feature(res)
    return res.__geo_interface__


def fixed_geometry(
        feature: geojson.Feature,
        fix_longitude: bool = False,
        fix_antimeridian: bool = False,
) -> geojson.Feature:
    """
    Fixes a feature's geometry in-place.

    Note: This may cut off parts of the supposed polygon.

    :param feature:
    :param fix_longitude: Flag signaling whether to adapt longitudes such that they are between \
    -180 and 180 deg. Longitudes outside of this interval are translated by multiples of 360 to \
    fall inside.
    :param fix_antimeridian:
    :return:
    """
    if feature['geometry']['type'] not in ['Polygon', 'MultiPolygon']:
        return feature  # pragma: no cover
    if feature['geometry']['type'] == 'Polygon':
        feature['geometry'] = dict(
            type='MultiPolygon', coordinates=[feature['geometry']['coordinates']])
    fixed = False
    if fix_longitude:
        new_polys = []
        polys = feature['geometry']['coordinates'] if feature['geometry']['type'] == 'MultiPolygon'\
            else [feature['geometry']['coordinates']]
        for i, poly in enumerate(polys):
            rings = []
            for ring in poly:
                if fix_longitude:
                    coords = []
                    for lon, lat in ring:
                        flon = correct_longitude(lon)
                        if flon != lon:
                            fixed = True
                            lon = flon
                        coords.append([lon, lat])
                    ring = coords
                rings.append(ring)
            new_polys.append(rings)
    if fixed:  # Make sure we only fix what's broken!
        new_feature = geojson.get_feature(dict(type='MultiPolygon', coordinates=new_polys), {})
    else:
        new_feature = feature
    if fix_antimeridian:
        for poly in feature['geometry']['coordinates']:
            if min(c[0] for c in poly[0]) < 0 and max(c[0] for c in poly[0]) > 0:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    new_feature = antimeridian.fix_geojson(new_feature)
                break
    geom = shape(new_feature['geometry'])
    for fixer in ShapelyChecker, SpherelyChecker:
        geom = fixer.fixer(geom)
    check_feature(geom, feature)
    feature['geometry'] = geom.__geo_interface__
    return feature


def shapely_simplified_geometry(
        feature: geojson.Feature,
        tolerance: float = 0.001,
) -> geojson.Feature:
    """
    With the default tolerance of 0.001, typical geo features with detailed coastlines will be
    reduced (in terms of GeoJSON size) by a factor of 10.
    """
    feature['geometry'] = geojson.get_geometry(
        simplify(shape(feature['geometry']), tolerance=tolerance))
    return feature


def azimuth(p1, p2):
    """Calculate azimuth from p1 to p2 (degrees from north, clockwise)."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return np.degrees(np.arctan2(dx, dy)) % 360


def angle_at_vertex(p1, p2, p3):
    """
    Calculate interior angle at vertex p2 using azimuth-based approach (like QGIS).
    """
    azimuth1 = azimuth(p1, p2)  # Direction of incoming edge
    azimuth2 = azimuth(p2, p3)  # Direction of outgoing edge

    if azimuth1 > azimuth2 and azimuth1 > azimuth2 + 180:
        angle = 540 - azimuth1 + azimuth2
    elif azimuth1 > azimuth2:
        angle = 180 - azimuth1 + azimuth2
    elif azimuth1 < azimuth2 and azimuth1 + 180 > azimuth2:
        angle = 180 + azimuth2 - azimuth1
    else:  # azimuth1 < azimuth2 and azimuth1 + 180 <= azimuth2
        angle = azimuth2 - azimuth1 - 180

    return angle


def remove_spikes_by_angle(coords, min_angle=1.0):
    """Remove vertices with angles below min_angle threshold."""
    coords = list(coords)
    if len(coords) < 4:
        return coords  # pragma: no cover

    n = len(coords) - 1
    cleaned = [
        coords[i] for i in range(n)
        if angle_at_vertex(coords[(i - 1) % n], coords[i], coords[(i + 1) % n]) >= min_angle
    ]

    # Make sure start/end vertice is
    if cleaned and cleaned[0] != cleaned[-1]:
        cleaned.append(cleaned[0])

    return cleaned


def remove_spikes_from_polygon(geom, min_angle=1.0):
    """Remove spike vertices from polygon geometry."""
    if isinstance(geom, Polygon):
        exterior = remove_spikes_by_angle(geom.exterior.coords, min_angle)
        interiors = [
            remove_spikes_by_angle(ring.coords, min_angle)
            for ring in geom.interiors
        ]
        interiors = [i for i in interiors if len(i) >= 4]

        if len(exterior) >= 4:
            return Polygon(exterior, interiors)
        return None  # pragma: no cover

    elif isinstance(geom, MultiPolygon):
        polys = [remove_spikes_from_polygon(p, min_angle) for p in geom.geoms]
        polys = [p for p in polys if p is not None]
        return MultiPolygon(polys) if polys else None

    return geom  # pragma: no cover


def correct_longitude(lon: Union[int, float]) -> Union[int, float]:
    """
    Coerces a geographic longitude into the -180..180 degree range.
    """
    sign = -1 if lon < 0 else 1
    if abs(lon) > 180:
        lon = lon - sign * ((abs(lon) // 360) + 1) * 360
        if lon == -180:
            lon = 180
    return lon
