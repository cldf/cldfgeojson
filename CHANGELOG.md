# Changes

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
