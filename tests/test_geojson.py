import pytest
from shapely.geometry import shape

from cldfgeojson.geojson import *


@pytest.mark.parametrize(
    'type_,coords,check',
    [
        ('Point', [-170, 0], lambda s: s.x > 0),
        ('MultiPoint', [[-170, 0], [170, 0]], lambda s: s.centroid.x == 180),
        ('Polygon', [[[170, 0], [-170, 1], [-170, -1], [170, 0]]], lambda s: s.centroid.x > 180),
        ('MultiPolygon',
         [[[[170, 0], [-170, 1], [-170, -1], [170, 0]]]],
         lambda s: s.centroid.x > 180)
    ]
)
def test_pacific_centered(type_, coords, check):
    assert check(shape(pacific_centered(dict(type=type_, coordinates=coords))))
