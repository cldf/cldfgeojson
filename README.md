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
