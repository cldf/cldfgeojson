# cldfgeojson

[![Build Status](https://github.com/cldf/cldfgeojson/workflows/tests/badge.svg)](https://github.com/cldf/cldfgeojson/actions?query=workflow%3Atests)
[![PyPI](https://img.shields.io/pypi/v/cldfgeojson.svg)](https://pypi.org/project/cldfgeojson)

`cldfgeojson` provides tools to work with geographic data structures encoded as [GeoJSON](https://geojson.org)
in the context of [CLDF](https://cldf.clld.org) datasets.


## Install

```shell
pip install cldfgeojson
```


## Adding speaker areas to CLDF datasets

The functionality in [`cldfgeojson.create`](src/cldfgeojson/create.py) helps adding speaker area
information when creating CLDF datasets (e.g. with [`cldfbench`](https://github.com/cldf/cldfbench)).


## `leaflet.draw`

This package contains the [`leaflet.draw`](https://github.com/Leaflet/Leaflet.draw) plugin in the form of `data://` URLs in 
[a mako template](src/cldfgeojson/commands/templates/leaflet.draw.mako). `leaflet.draw` is
distributed under a MIT license:

> Copyright 2012-2017 Jon West, Jacob Toye, and Leaflet
> 
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
> 
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

