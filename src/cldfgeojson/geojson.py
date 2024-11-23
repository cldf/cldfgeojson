import json
import typing
import collections

from clldutils import jsonlib

__all__ = ['MEDIA_TYPE', 'Geometry', 'Feature', 'pacific_centered', 'dump', 'dumps']

# See https://datatracker.ietf.org/doc/html/rfc7946#section-12
MEDIA_TYPE = 'application/geo+json'


JSONObject = typing.Dict[str, typing.Any]


class Geometry(typing.TypedDict):
    """
    A Geometry object represents points, curves, and surfaces in
    coordinate space.  Every Geometry object is a GeoJSON object no
    matter where it occurs in a GeoJSON text.

    Note: We exclude geometries of type "GeometryCollection" in order to force presence
    of a "coordinates" member.

    See https://datatracker.ietf.org/doc/html/rfc7946#section-3.1
    """
    type: str
    coordinates: list


class Feature(typing.TypedDict, total=False):
    """
    See https://datatracker.ietf.org/doc/html/rfc7946#section-3.2
    """
    type: str
    geometry: Geometry
    properties: typing.Union[None, JSONObject]
    id: typing.Union[str, float, int]
    bbox: list


def pacific_centered(obj: typing.Union[Geometry, Feature]) -> typing.Union[Geometry, Feature]:
    """
    Adjust longitudes of coordinates of objects to force a pacific-centered position in place.

    Some mapping tools do not support "continuous worlds", i.e. displaying the same content at
    360° longitude increments. A typical workaround is "moving" objects to the appropriate "world
    copy". The same workaround also works for tools like shapely, which do maths in the cartesian
    plane, to avoid problems caused by the antimeridian.

    For language data, it is often useful to display pacific-centered maps, in order to not cut
    through the area of any language family. For this purpose, 154°E is a suitable central
    longitude, because the cut at 26°W does not cut through any macroareas. See
    https://en.wikipedia.org/wiki/154th_meridian_east and
    https://en.wikipedia.org/wiki/26th_meridian_west

    :return:
    """
    PACIFIC_CENTERED = 154

    def fix_position(pos):
        pos = list(pos)
        if pos[0] <= PACIFIC_CENTERED - 180:
            # Anything west of 26°W is moved by 360°.
            pos[0] += 360
        return pos

    geom = obj['geometry'] if 'geometry' in obj else obj
    if geom['type'] == 'Point':
        # Point -> [lon, lat]
        geom['coordinates'] = fix_position(geom['coordinates'])
    elif geom['type'] in {'MultiPoint', 'LineString'}:
        # MultiPoint -> [[lon, lat]..]
        # LineString -> [[lon, lat]..]
        geom['coordinates'] = [fix_position(pos) for pos in geom['coordinates']]
    elif geom['type'] in {'Polygon', 'MultiLineString'}:
        # Polygon -> [[[lon, lat]..]..]
        # MultiLineString -> [[[lon, lat]..]..]
        geom['coordinates'] = [[fix_position(pos) for pos in line] for line in geom['coordinates']]
    else:
        # MultiPolygon -> [[[[lon, lat]..]..]..]
        assert geom['type'] == 'MultiPolygon'
        geom['coordinates'] = [[[
            fix_position(pos) for pos in line] for line in poly] for poly in geom['coordinates']]

    return obj


#
# To make GeoJSON as small as possible, we provide functionality to write GeoJSON with coordinates
# limited to 5 decimal places, corresponding to a precision of ~1m.
#
class FloatWrapper:
    """
    In order to use the extension mechanism of Python's json.JSONEncode, we have to wrap floats in
    an "unknown" type.
    """
    def __init__(self, value):
        self.value = value


def wrap_floats(obj, in_coordinates=False):
    """
    Turns a GeoJSON object into one with all coordinates wrapped in FloatWrapper instances.

    :param obj:
    :param in_coordinates:
    :return:
    """
    if isinstance(obj, (list, tuple)):
        return [wrap_floats(item, in_coordinates=in_coordinates) for item in obj]
    if isinstance(obj, dict):
        # Detect whether we are in the "coordinates" array of a GeoJSON object.
        return collections.OrderedDict(
            (k, wrap_floats(v, in_coordinates=True if k == 'coordinates' else in_coordinates))
            for k, v in obj.items())
    if isinstance(obj, float) and in_coordinates:
        return FloatWrapper(obj)
    return obj


class MeterPrecisionFloatEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, FloatWrapper):
            return round(obj.value, 5)
        return super().default(obj)


def dump(obj, *args, **kw):
    kw['cls'] = MeterPrecisionFloatEncoder
    return jsonlib.dump(wrap_floats(obj), *args, **kw)


def dumps(obj, **kw):
    kw['cls'] = MeterPrecisionFloatEncoder
    return json.dumps(wrap_floats(obj), **kw)
