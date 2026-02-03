from shapely.geometry import shape, Point

from cldfgeojson.create import *


def test_feature_collection():
    assert 'type' in feature_collection([])


def test_aggregate(glottolog_cldf):
    def make_feature(latoffset=0, lonoffset=0):
        return {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-90 + lonoffset, 35 + latoffset],
                    [-90 + lonoffset, 30 + latoffset],
                    [-85 + lonoffset, 30 + latoffset],
                    [-85 + lonoffset, 35 + latoffset],
                    [-90 + lonoffset, 35 + latoffset]
                ]]
            }
        }

    shapes = [
        (1, make_feature(latoffset=10), 'berl1235'),  # a dialect
        (2, make_feature(lonoffset=10), 'stan1295'),  # a language
        (3, make_feature(), 'high1289'),  # a subgroup
        (4, make_feature(), 'abin1243'),  # an isolate
    ]
    features, langs = aggregate(
        shapes,
        glottolog_cldf,
    )
    assert len(langs) == 2
    for feature, (glang, pids, fam) in zip(features, langs):
        if glang.id == 'stan1295':
            break
    assert len(pids) == 2
    # Make sure a point from the dialect polygon is in the merged language feature:
    assert shape(feature['geometry']).contains(Point(-87, 42))
    # Make sure a point from the sub-group polygon is **not** in the merged feature:
    assert not shape(feature['geometry']).contains(Point(-87, 33))

    features, langs = aggregate(
        shapes,
        glottolog_cldf,
        level='family',
    )
    assert len(langs) == 2
    for feature, (glang, pids, fam) in zip(features, langs):
        if glang.id == 'abin1243':
            assert fam is None
        if glang.id == 'indo1319':
            break
    assert len(pids) == 3
    # Make sure a point from the sub-group polygon is in the merged feature:
    assert shape(feature['geometry']).contains(Point(-87, 33))
