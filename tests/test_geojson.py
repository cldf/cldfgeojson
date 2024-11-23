import json
import decimal

import pytest
from numpy.ma.testutils import approx
from shapely.geometry import shape
from clldutils.jsonlib import load

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


def test_dumps(tmp_path):
    with pytest.raises(TypeError):
        dumps(decimal.Decimal('1'))

    c = 1.23456789
    assert '1.2345678' in json.dumps(c)
    obj = json.loads(dumps({'properties': {'a': c}, 'coordinates': [[c], c]}))
    assert approx(obj['properties']['a'], c)
    assert approx(obj['coordinates'][0][0], 1.23456)

    p = tmp_path / 'test.geojson'
    dump({'properties': {'a': c}, 'coordinates': [[c], c]}, p)
    obj = load(p)
    assert approx(obj['properties']['a'], c)
    assert approx(obj['coordinates'][0][0], 1.23456)
