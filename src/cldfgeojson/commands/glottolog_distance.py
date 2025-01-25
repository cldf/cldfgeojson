"""
Compute the distance between speaker areas in a CLDF dataset and corresponding Glottolog point
coordinates.

Distances are given in "grid units", i.e. - since input is given as WGS 84 coordinates - in degrees
Thus, near the equator, a distance of 1 would equal roughly 111km, while further away from the
equator it will be less.

To get an overview of Glottolog distances for a dataset you may pipe the output to the csvstat
tool:

cldfbench geojson.glottolog_distance path/to/cldf --glottolog path/to/glottolog --format tsv | \
csvstat -t

You can also print the distances to the terminal using a tool like termgraph:

cldfbench geojson.glottolog_distance path/to/cldf --glottolog path/to/glottolog --format tsv | \
sed '/^$/d' | csvcut -t -c ID,Distance | csvsort -c Distance | csvformat -E | termgraph
"""  # noqa: E501
from clldutils.clilib import Table, add_format
from shapely.geometry import Point, shape, MultiPolygon
from pycldf.cli_util import add_dataset, get_dataset, add_catalog_spec
from tqdm import tqdm

from cldfgeojson.util import speaker_area_shapes


def register(parser):
    add_dataset(parser)
    add_catalog_spec(parser, 'glottolog')
    add_format(parser, 'simple')


def run(args):
    ds = get_dataset(args)
    geojsons = speaker_area_shapes(ds, fix_geometry=True)
    gl_coords = {
        lg.id: Point(float(lg.longitude), float(lg.latitude))
        for lg in args.glottolog.api.languoids() if lg.longitude}

    with Table(args, 'ID', 'Distance', 'Contained', 'NPolys') as t:
        for i, lg in tqdm(enumerate(ds.objects('LanguageTable'), start=1)):
            if lg.cldf.glottocode in gl_coords:
                if lg.cldf.speakerArea in geojsons:
                    shp = geojsons[lg.cldf.speakerArea][lg.cldf.id]
                elif lg.cldf.speakerArea:  # pragma: no cover
                    shp = shape(lg.speaker_area_as_geojson_feature['geometry'])
                else:
                    continue

                npolys = len(shp.geoms) if isinstance(shp, MultiPolygon) else 1
                gl_coord = gl_coords[lg.cldf.glottocode]
                if shp.contains(gl_coord):
                    t.append((lg.id, 0, True, npolys))
                elif shp.convex_hull.contains(gl_coord):
                    t.append((lg.id, 0, False, npolys))  # pragma: no cover
                else:
                    dist = shp.distance(gl_coord)
                    if dist > 180:
                        dist = abs(dist - 360)  # pragma: no cover
                    t.append((lg.id, dist, False, npolys))
