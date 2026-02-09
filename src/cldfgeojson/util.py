import typing

from shapely.geometry import shape
from pycldf import Dataset
from pycldf.media import MediaTable

from cldfgeojson.geojson import MEDIA_TYPE
from cldfgeojson.geometry import fixed_geometry


def speaker_area_shapes(ds: Dataset,
                        fix_geometry: bool = False,
                        with_properties: bool = False) -> typing.Tuple[
                            typing.Dict[str, typing.Dict[str, shape]],
                            typing.Dict[str, typing.Dict[str, shape]]]:
    """
    Read all speaker areas from GeoJSON files provided with a dataset.

    :param ds:
    :param fix_geometry:
    :return:
    """
    geojsons_by_gc, geojsons_by_id = {}, {}
    for media in MediaTable(ds):
        if media.mimetype == MEDIA_TYPE:
            geojson = media.read_json()
            if 'features' in geojson:
                #
                # FIXME: do validity check right here!
                #
                geojsons_by_gc[media.id] = {}
                geojsons_by_id[media.id] = {}
                for f in geojson['features']:
                    if with_properties:
                        geojsons_by_id[media.id][f['properties'].get('id')] = \
                            (shape(f['geometry']), f['properties'])
                    else:
                        geojsons_by_id[media.id][f['properties'].get('id')] = shape(f['geometry'])
                    if f['properties'].get('cldf:languageReference'):
                        for lid in [f['properties']['cldf:languageReference']] \
                                if isinstance(f['properties']['cldf:languageReference'], str) \
                                else f['properties']['cldf:languageReference']:
                            if fix_geometry:
                                f = fixed_geometry(f)
                            if with_properties:
                                geojsons_by_gc[media.id][lid] = \
                                    (shape(f['geometry']), f['properties'])
                            else:
                                geojsons_by_gc[media.id][lid] = shape(f['geometry'])
    return geojsons_by_gc, geojsons_by_id
