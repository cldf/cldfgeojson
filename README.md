# cldfgeojson

[![Build Status](https://github.com/cldf/cldfgeojson/workflows/tests/badge.svg)](https://github.com/cldf/cldfgeojson/actions?query=workflow%3Atests)
[![PyPI](https://img.shields.io/pypi/v/cldfgeojson.svg)](https://pypi.org/project/cldfgeojson)

`cldfgeojson` provides tools to work with geographic data structures encoded as [GeoJSON](https://geojson.org)
in the context of [CLDF](https://cldf.clld.org) datasets.


## Install

```shell
pip install cldfgeojson
```


## Creating CLDF datasets with speaker area data in GeoJSON

The functionality in [`cldfgeojson.create`](src/cldfgeojson/create.py) helps adding speaker area
information when creating CLDF datasets (e.g. with [`cldfbench`](https://github.com/cldf/cldfbench)).


## Working around [Antimeridian problems](https://antimeridian.readthedocs.io/en/stable/)

Tools like `shapely` allow doing geometry with shapes derived from GeoJSON, e.g. computing
intersections or centroids. But `shapely` considers coordinates to be in the cartesian plane rather
than on the surface of the earth. While this works generally well enough close to the equator, it
fails for geometries crossing the antimeridian. To prepare GeoJSON objects for investigation with
`shapely`, we provide a function that "moves" objects on a - somewhat linguistically informed -
pacific-centered cartesian plane: longitudes less than 26°W are adapted by adding 360°, basically
moving the interval of valid longitudes from -180°..180° to -26°..334°. While this just moves the
antimeridian problems to 26°W, it's still useful because most spatial data about languages does not
cross 26°W - which cannot be said for 180°E because this longitude is crosssed by the speaker area
of the Austronesian family.

```python
>>> from cldfgeojson.geojson import pacific_centered
>>> from shapely.geometry import shape
>>> p1 = shape({"type": "Point", "coordinates": [179, 0]})
>>> p2 = shape({"type": "Point", "coordinates": [-179, 0]})
>>> p1.distance(p2)
358.0
>>> p1 = shape(pacific_centered({"type": "Point", "coordinates": [179, 0]}))
>>> p2 = shape(pacific_centered({"type": "Point", "coordinates": [-179, 0]}))
>>> p1.distance(p2)
2.0
```


## Manipulating geo-referenced images in GeoTIFF format

The [`cldfgeojson.geotiff`](src/cldfgeojson/geotiff.py) module provides functionality related to
images in [GeoTIFF](https://en.wikipedia.org/wiki/GeoTIFF) format.


## Commandline interface

`cldfgeojson` also provides [`cldfbench` sub-commands](https://github.com/cldf/cldfbench?tab=readme-ov-file#commands):

- [`geojson.validate`](src/cldfgeojson/commands/validate.py)
- [`geojson.glottolog_distance`](src/cldfgeojson/commands/glottolog_distance.py)
- [`geojson.webmercator`](src/cldfgeojson/commands/webmercator.py)
- [`geojson.overlay`](src/cldfgeojson/commands/overlay.py)


## `leaflet.draw`

This package contains the [`leaflet.draw`](https://github.com/Leaflet/Leaflet.draw) plugin in the form of `data://` URLs in 
[a mako template](src/cldfgeojson/commands/templates/leaflet.draw.mako). `leaflet.draw` is
distributed under a MIT license:

> Copyright 2012-2017 Jon West, Jacob Toye, and Leaflet
> 
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
> 
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

