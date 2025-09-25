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

`cldfgeojson` also provides [`cldfbench` sub-commands](https://github.com/cldf/cldfbench?tab=readme-ov-file#commands).
These are particularly useful to validate GeoJSON speaker areas during dataset creation/curation.


### `geojson.validate`

The[`geojson.validate`](src/cldfgeojson/commands/validate.py) command can be used to make sure GeoJSON [Polygon](https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.6) 
and [MultiPolygon](https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.7) geometries for speaker
areas are valid. (For a short explanation what this validity entails, see https://postgis.net/workshops/postgis-intro/validity.html .)

The dataset used for testing this package contains one invalid geometry, which can be detected and
reported running
```shell
$ cldfbench geojson.validate tests/fixtures/dataset/
id        glottocode    reason                        fixable
--------  ------------  ----------------------------  ---------
bare1276  abcd1234      Ring Self-intersection[15 5]  True
```

### `geojson.glottolog_distance`

While speakers of languages, and thus the "language area", can move around over time, for most
languages and the timespan since the languages have been described in the literature this has not
happened on a large scale. Thus, comparing speaker areas reported in a dataset to the corresponding
point coordinates for the languages as reported by [Glottolog](https://glottolog.org) is a good
plausibility check which will detect issues such as mistyped Glottocodes, etc.

Such a comparison is provided by the [`geojson.glottolog_distance`](src/cldfgeojson/commands/glottolog_distance.py) command, which computes
the distances between speaker area (Multi)Polygons and Glottolog's point coordinate. To keep the
implementation simple, this computation is done with [`shapely`](https://shapely.readthedocs.io/en/stable/),
which allows for "analysis of geometric objects in the Cartesian plane". Thus, distances are reported
in "grid units" of a geographic coordinate system and require some interpretation. Close to the equator,
where we find the biggest linguistic diversity, one grid unit roughly equals a distance of 110km on the
globe, whereas closer to the poles it may be less. A distance of 0 means that the speaker area
(or its convex hull, taking into account that Glottolog's point coordinate is often chosen as some
sort of midpoint in cases of spread out, disjoint speaker populations) contains the Glottolog coordinate.

The command needs to access the [Glottolog data](https://github.com/glottolog/glottolog). To do so, 
a local clone or [export of a specific version](https://github.com/glottolog/glottolog/releases) must be available.
The path to clone or export must be passed as value of the `--glottolog` option. If a full clone is
available, a particular release may be selected by passing the relese tag as value of the `--glottolog-version`
option.

As an example, we can compute Glottolog distances for the speaker areas of Uralic languages as
reported in the [the CLDF dataset derived from Rantanen et al.'s "Geographical database of the Uralic languages"](https://github.com/cldf-datasets/rantanenurageo). Assuming this dataset is downloaded to `rantanenurageo`
and Glottolog data is available at `glottolog`, we can run
```shell
cldfbench geojson.glottolog_distance rantanenurageo/cldf --glottolog glottolog
```
and get a (long) listing the results printed to the screen.
Since we are typically interested in the outliers, i.e. cases where the Glottolog coordinate is not
contained in the area, we can just use `grep` to filter the result list:
```shell
cldfbench geojson.glottolog_distance rantanenurageo/cldf --glottolog glottolog  | grep False
Ingrian                                0.00  False              13
Karelian                               0.00  False              16
...
```
But we can also make use of the `--format` option to create TSV output which we can then manipulate with
the [`csvkit`](https://csvkit.readthedocs.io/en/latest/) tools to give a better overview:
```shell
cldfbench geojson.glottolog_distance rantanenurageo/cldf --glottolog glottolog --format tsv | csvformat -t | csvsort -c Distance | csvcut -c ID,Distance
...
KomiYazva,1.0292353508840884
EasternMari,1.6462432136183747
KarelianLivvi,2.431383058632656
TomskregionSelkupSouthernSelkup,2.4567889514058106
```


### `geojson.multipolygon_spread` 

The[`geojson.multipolygon_spread`](src/cldfgeojson/commands/glottolog_distance.py) command provides another
check for the plausibility of Glottocode assignments to the speaker areas reported in a dataset. Sometimes
datasets assign dialect-level Glottocodes to polygons and later aggregate these polygons to compute the
area for the parent language. Incorrect Glottocode assignments may then result in a language area containing
one outlier polygon, i.e. one polygon which is far away from the rest of the area.

With `geojson.multipolygon_spread` we compute the spread of polygons which are aggregated into a single
language area. High spread may be a symptom of wrong Glottocode assignment. Of course, the spread numbers
need interpretation as well. For languages spoken on multiple islands in the pacific a spread > 5 may
be expected, while for languages spoken in [Morobe province (Papua New Guinea)](https://glottolog.org/glottolog/language.map.html?country=PG#8/-5.665/146.692) 
a spread > 2 already means that polygons of the area are probably separated by at least one different
language area.

The options and output of `geojson.multipolygon_spread` are largely the same as for `geojson.glottolog_distance`.
A row in the dataset's `LanguageTable` is considered to represent a language-level Glottolog languoid 
either if `LanguageTable` contains a column named `Glottolog_Languoid_Level` with the value `language`
or if the [`glottocode`](http://cldf.clld.org/v1.0/terms.rdf#glottocode) column of `LanguageTable`
specifies a language-level Glottolog languoid.
(In the latter case, access to Glottolog data is necessary, see above.)


### `geojson.geojson`

While most of the GeoJSON data that comes with CLDF datasets can be loaded as such directly in tools
like QGIS, it is sometimes useful to inspect only subsets of the data. The [`geojson.geojson`](src/cldfgeojson/commands/geojson.py)
command creates GeoJSON representations of configurable subsets of the speaker areas reported in a
dataset. This command is intended to be used in tandem with the validation commands above. I.e. the
output of the commands above can be manipulated, filtered and pruned to a simple list of language `ID`s
which can then serve as input to `geojson.geojson`.

A full example of this workflow would look as follows:
```shell
cldfbench geojson.glottolog_distance rantanenurageo/cldf --glottolog glottolog --format tsv | \
csvformat -t | \
csvgrep -c Distance -i -r"^0" | \
csvcut -c ID | csvformat -E | \
cldfbench geojson.geojson rantanenurageo/cldf -
```
and result in GeoJSON looking as follows when viewed via https://geojson.io/
![](tests/geojson.geojson.png)
where the point markers locate the Glottolog coordinates and the polygons represent the speaker
areas reported in the dataset.


### Other commands

- [`geojson.compare`](src/cldfgeojson/commands/compare.py)
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

