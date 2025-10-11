# Changes


## unreleased

- Support aggregation on Glottolog dialect level as well.
- It turns out that fixing polygons may also create artefacts of type `MultiPoint`.
- Fixed problem where `geojson.multipolygon_spread` relied on a `Glottolog_Languoid_Level` column
  being present.


## [1.5.1] - 2025-04-11

Fixed bug in `compare` command whereby an incorrect GeoJSON feature for a language might have been
selected from the second dataset.


## [1.5.0] - 2025-04-09

Added a command to compare speaker areas for the same languages from two CLDF datasets.


## [1.4.0] - 2025-02-10

- Added command to write selected speaker areas from a dataset to GeoJSON, optionally including
  corresponding Glottolog point coordinates.
- Added function to simplify the geometry of a feature (in order to reduce the size of the resulting
  GeoJSON).


## [1.3.0] - 2025-01-28

- Added command to compute multi-polygon spread for speaker areas of language-level items in the
  LanguageTable of a CLDF dataset.


## [1.2.0] - 2025-01-25

- Added command to validate speaker area geometries.
- Added function to repair geometries using `shapely.make_valid`.


## [1.1.0] - 2024-11-23

- Dropped support for python 3.8, added support for python 3.13.
- Added command to compute distances between areas and Glottolog point coordinates.
- Added functions to write more compact GeoJSON by limiting float precision to 5 decimal places.


## [1.0.0] - 2024-06-19

Added function to translate GeoJSON objects to be "pacific centered".


## [0.4.0] - 2024-06-11

- Enhanced `fixed_geometry`, adding option to fix antimeridian issues.
- Moved functionality to manipulate GeoTIFF files to separate module to enhance
  reusability.


## [0.3.0] - 2024-05-31

- Make sure we can also convert 4-band input to usable JPEG in webmercator projection.
- Bind popups to included GeoJSON layers in leaflet output.


## [0.2.1] - 2024-05-17

- Subtract buffer from merged geometries after merging.


## [0.2.0] - 2024-04-26

- Allow specifying buffer when aggregating shapes.
- Provide symbols for import on package level.


## [0.1.0] - 2024-04-25

Functionality to add speaker area information to CLDF datasets
