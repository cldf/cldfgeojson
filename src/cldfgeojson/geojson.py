import typing

__all__ = ['MEDIA_TYPE', 'Geometry', 'Feature']

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
