import typing

from shapely.geometry import shape
from pycldf import Dataset
from pycldf.media import MediaTable

from cldfgeojson.geojson import MEDIA_TYPE
from cldfgeojson.create import shapely_fixed_geometry


def speaker_area_shapes(ds: Dataset,
                        fix_geometry: bool = False) -> typing.Dict[str, typing.Dict[str, shape]]:
    """
    Read all speaker areas from GeoJSON files provided with a dataset.

    :param ds:
    :param fix_geometry:
    :return:
    """
    geojsons = {}
    for media in MediaTable(ds):
        if media.mimetype == MEDIA_TYPE:
            geojson = media.read_json()
            if 'features' in geojson:
                geojsons[media.id] = {}
                for f in geojson['features']:
                    if f['properties'].get('cldf:languageReference'):
                        for lid in [f['properties']['cldf:languageReference']] \
                                if isinstance(f['properties']['cldf:languageReference'], str) \
                                else f['properties']['cldf:languageReference']:
                            if fix_geometry:
                                f = shapely_fixed_geometry(f)
                            geojsons[media.id][lid] = shape(f['geometry'])
    return geojsons
