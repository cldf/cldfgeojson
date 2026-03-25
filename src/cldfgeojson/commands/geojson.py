"""
Create a GeoJSON file containing speaker area features from a dataset for selected language IDs.

This command is particularly useful to create a GeoJSON file to inspect cases of high distances
between a speaker area and the corresponding Glottolog point coordinate.

It is also possible to add speaker areas from two CLDF datasets. To do so, use the `--dataset2`
option and pass Glottocodes as language identifiers.
"""  # noqa: E501
import dataclasses
import sys
import json
import itertools
from typing import Any

from pycldf.cli_util import add_dataset, get_dataset, UrlOrPathType
from pycldf.ext import discovery
from clldutils.color import qualitative_colors

from cldfgeojson.util import speaker_area_shapes, ShapeDictType
from cldfgeojson.create import feature_collection


def arg_or_stdin(s):
    if s == '-':
        return sys.stdin.read().splitlines()  # pragma: no cover
    return s


def register(parser):  # pylint: disable=C0116
    add_dataset(parser)
    parser.add_argument('language_ids', type=arg_or_stdin, nargs='+')
    parser.add_argument('--no-glottolog', action='store_true', default=False)
    parser.add_argument(
        '--glottolog',
        metavar='GLOTTOLOG',
        help='Path to repository clone of Glottolog data')
    parser.add_argument(
        '--glottolog-version',
        help='Version of Glottolog data to checkout',
        default=None)
    parser.add_argument(
        '--dataset2',
        metavar='DATASET2',
        help="Dataset locator (i.e. URL or path to a CLDF metadata file or to the data file). "
             "Resolving dataset locators like DOI URLs might require installation of third-party "
             "packages, registering such functionality using the `pycldf_dataset_resolver` "
             "entry point.",
        type=UrlOrPathType(),
    )


def _get_geojsons(ds2):
    assert ds2
    lid2gc = {
        lg.id: (lg.cldf.speakerArea, lg.cldf.glottocode)
        for lg in ds2.objects('LanguageTable') if lg.cldf.glottocode}
    geojsons2 = {}
    for fid, d in speaker_area_shapes(ds2, fix_geometry=True, with_properties=True)[0].items():
        for lid, v in d.items():
            if lid in lid2gc and fid == lid2gc[lid][0]:
                geojsons2[lid2gc[lid][1]] = v
    return geojsons2


def run(args):  # pylint: disable=C0116,R0912
    lids = set(itertools.chain.from_iterable(
        obj if isinstance(obj, list) else [obj] for obj in args.language_ids))
    colors = dict(zip(lids, qualitative_colors(len(lids))))

    ds = get_dataset(args)
    geojsons: ShapeDictType = speaker_area_shapes(ds, fix_geometry=True, with_properties=True)[0]
    ds2, geojsons2 = None, {}
    if args.dataset2:
        ds2 = discovery.get_dataset(args.dataset2, download_dir=args.download_dir)
        geojsons2 = _get_geojsons(ds2)

    gl = {}
    if args.glottolog and not args.no_glottolog:
        gl = {lg.id: lg for lg in args.glottolog.api.languoids() if lg.longitude}

    features = Features()
    for lg in ds.objects('LanguageTable'):
        if (ds2 is None and lg.id in lids) or (ds2 and lg.cldf.glottocode in lids):
            if lg.cldf.speakerArea in geojsons:
                geom, props = geojsons[lg.cldf.speakerArea][lg.cldf.id]
            elif lg.cldf.speakerArea:  # pragma: no cover
                feature = lg.speaker_area_as_geojson_feature
                geom, props = feature['geometry'], feature['properties']
            else:  # pragma: no cover
                args.log.warning('No speaker area for language ID %s', lg.id)
                continue

            for k, v in lg.data.items():
                if k not in {'ID', 'Name', 'Latitude', 'Longitude', 'Glottocode'}:
                    props.setdefault(k, str(v))
            props.update({
                'title': f'{lg.id}: {lg.cldf.name}',
                "stroke": colors[lg.cldf.glottocode if ds2 else lg.id],
                "fill": '#0000ff' if ds2 else colors[lg.cldf.glottocode if ds2 else lg.id],
                "fill-opacity": 0.3 if ds2 else 0.5,
            })
            features.add(geom, props)
            if ds2 and lg.cldf.glottocode in geojsons2:
                geom, props = geojsons2[lg.cldf.glottocode]
                props.update({
                    'title': f"{lg.cldf.glottocode}: {props.get('title') or props.get('name')}",
                    "stroke": colors[lg.cldf.glottocode if ds2 else lg.id],
                    "fill": "#ff0000",
                    "fill-opacity": 0.3,
                })
                features.add(geom, props)

            if args.glottolog:
                if lg.cldf.glottocode in gl:
                    glang = gl[lg.cldf.glottocode]
                    features.add(
                        {'type': 'Point', 'coordinates': [glang.longitude, glang.latitude]},
                        {
                            'title': f'{lg.id} -> {glang.id}: {glang.name}',
                            "marker-color": colors[lg.id]})
                else:  # pragma: no cover
                    args.log.warning('No Glottolog coordinate for language ID %s', lg.id)
    print(json.dumps(feature_collection(features), indent=2))


class Features(list):
    def add(self, geometry: dict[str, Any], properties: dict[str, Any]):
        if hasattr(geometry, '__geo_interface__'):
            geometry = geometry.__geo_interface__
        self.append({'type': 'Feature', 'geometry': geometry, 'properties': properties})
