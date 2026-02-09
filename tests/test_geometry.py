import pytest

from shapely.geometry import Point
from clldutils.jsonlib import load

from cldfgeojson.geometry import *


@pytest.mark.parametrize(
    'in_,out_',
    [
        (0, 0),
        (1, 1),
        (-1, -1),
        (180, 180),
        (-180, -180),
        (181, -179),
        (540, 180),
        (-900, 180),
        (-181, 179),
    ]
)
def test_correct_longitude(in_, out_):
    assert correct_longitude(in_) == out_


@pytest.mark.parametrize(
    'tolerance,reduction',
    [
        (0.1, 50),
        (0.01, 40),
        (0.001, 10),  # the default
        (0.0001, 1.1),
    ]
)
def test_shapely_simplified_geometry(fixtures_dir, tolerance, reduction):
    f = load(fixtures_dir / 'irish.geojson')
    size = len(json.dumps(f))
    shapely_simplified_geometry(f, tolerance=tolerance)
    assert size / (2 * reduction) < len(json.dumps(f)) < size / reduction


def test_check_feature(tmp_path):
    geom = shape({
        "type": "Polygon",
        "coordinates": [[  # A self-intersecting polygon.
            [5, 0],
            [-5, 0],
            [-5, 5],
            [0, 5],
            [0, -5],
            [5, -5],
            [5, 0],
        ]]
    })
    with pytest.raises(ValueError):
        check_feature(geom, tdir=tmp_path)
    assert tmp_path.glob('*.geojson')


def test_fixed_geometry(recwarn):
    f = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-10, -10],
                    [-10, 10],
                    [10, 10],
                    [10, -10],
                    [-10, -10],
                ],
                [
                    [-5, -5],
                    [-5, 5],
                    [5, 5],
                    [5, -5],
                    [-5, -5],
                ],
            ]
        }
    }
    assert not shape(f['geometry']).contains(Point(0, 0))
    res = fixed_geometry(f)
    assert not shape(res['geometry']).contains(Point(0, 0))
    assert fixed_geometry(f)

    f = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [5, 0],
                [-5, 0],
                [-5, 5],
                [0, 5],
                [0, -5],
                [5, -5],
                [5, 0],
            ]]
        }
    }
    res = fixed_geometry(f)
    assert res['geometry']['type'] == 'MultiPolygon'
    assert shape(res['geometry']).contains(Point(-2, 2))
    assert not shape(res['geometry']).contains(Point(2, 2))
    assert fixed_geometry(f)

    f = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [[
                    [5, 0],
                    [-5, 0],
                    [-5, 5],
                    [0, 5],
                    [0, -5],
                    [5, -5],
                    [5, 0],
                ]],
                [[
                    [370, 5],
                    [15, 5],
                    [15, 10],
                    [10, 10],
                    [10, 5],
                ]],
            ]
        }
    }
    res = fixed_geometry(f, fix_longitude=True)
    assert shape(res['geometry']).contains(Point(12, 7))
    assert fixed_geometry(f)

    f = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [
                        -179.70358951407547,
                        52.750507455036264
                    ],
                    [
                        179.96672360880183,
                        52.00163609753924
                    ],
                    [
                        -177.89334479610974,
                        50.62805205289558
                    ],
                    [
                        -179.9847165338706,
                        51.002602948712465
                    ],
                    [
                        -179.70358951407547,
                        52.750507455036264
                    ]
                ]
            ]
        }
    }
    res = fixed_geometry(f, fix_antimeridian=True)
    assert res['geometry']['type'] == 'MultiPolygon'
    # Ideally, we'd want this geometry only cut into two polygons, but some interference from the
    # shapely fixing introduces another polygon ...
    assert len(res['geometry']['coordinates']) == 3
    assert fixed_geometry(f)


def test_SpherelyChecker(fixtures_dir):
    f = load(fixtures_dir / 'irish.geojson')
    _ = SpherelyChecker.fixer(shape(f['geometry']))

    f = load(fixtures_dir / 'maja1242.geojson')
    with pytest.raises(ValueError):
        _ = SpherelyChecker.fixer(shape(f['geometry']))

    f = load(fixtures_dir / 'spherely_fixed.geojson')
    _ = SpherelyChecker.fixer(shape(f['geometry']))

    f = load(fixtures_dir / 'spike_removal.geojson')
    _ = SpherelyChecker.fixer(shape(f['geometry']))
