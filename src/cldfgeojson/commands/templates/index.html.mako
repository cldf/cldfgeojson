<%namespace name="leafletdraw" file="leaflet.draw.mako"/>
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/purecss@3.0.0/build/pure-min.css"
          integrity="sha384-X38yfunGUhNzHpBaEBsWLO+A0HDYOQi8ufWDkZ0k9e0eXz/tH3II7uKZ9msv++Ls" crossorigin="anonymous">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    % if with_draw:
    ${leafletdraw.include()|n}
    % endif
    ##<title>${title}</title>
    <style>
        body, html, .vh {
            height: 100vh;
        }

        title {
            text-align: center;
            width: 100%;
        }

        #map {
            height: 100%;
            width: 100%;
        }

        #export-container {
            font-size: 12px;
            height: 100%;
            width: 100%;
            padding: 6px;
            border-radius: 4px;
        }
    </style>
</head>
<body>
<div class="vh pure-g">
    <div class="vh pure-u-4-5">
        <div id='map'></div>
    </div>
    <div class="vh pure-u-1-5">
        <div id="export-container">
            <div style="height: 10%">
                Opacity of image overlay:<br><input type="range" min="0" max="100" id="opacity" value="50">
                % if with_draw:
                <hr>
                <button id="delete" style="float: right;">Delete Features</button>
                <button id="export">Export Features</button>
            </div>
            <textarea id="ex" style="height: 90%; overflow-y: scroll; width: 100%"> </textarea>
            % endif
        </div>
    </div>
</div>
<script>
    const draw = ${'true' if with_draw else 'false'};
    const map = L.map('map').setView([37.8, -96], 4);
    var drawnItems = L.featureGroup().addTo(map);
    const geojson = ${geojson};
    const layers = {};

    const latLngBounds = L.latLngBounds([[${bounds[1]}, ${bounds[0]}], [${bounds[3]}, ${bounds[2]}]]);

    var osmUrl = 'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        osmAttrib = '&copy; <a href="http://openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        osm = L.tileLayer(osmUrl, {maxZoom: 20, attribution: osmAttrib});
    osm.addTo(map);
    if (draw) {
        map.addControl(new L.Control.Draw({
            edit: {featureGroup: drawnItems, poly: {allowIntersection: false}},
            draw: {polygon: {allowIntersection: false, showArea: true}}
        }));
    }
    const imageOverlay = L.imageOverlay(
        `${img}`, latLngBounds, {opacity: 0.5, interactive: true}).addTo(map);
    layers['image'] = imageOverlay;

    const input = document.querySelector("#opacity");
    input.addEventListener("input", (event) => {imageOverlay.setOpacity(event.target.value / 100)});
    if (draw) {
        map.on(L.Draw.Event.CREATED, function (event) {
            var layer = event.layer;
            drawnItems.addLayer(layer);
        });
        document.getElementById('delete').onclick = function (e) {
            drawnItems.clearLayers();
        }
        document.getElementById('export').onclick = function (e) {
            document.getElementById('ex').innerText = JSON.stringify(drawnItems.toGeoJSON());
        }
    }
    for (const name in geojson) {
        var layer = L.geoJSON(geojson[name]);
        layers[name] = layer;
        layer.addTo(map)
    }
    L.control.layers({}, layers).addTo(map);
    L.rectangle(latLngBounds).addTo(map);
    map.fitBounds(latLngBounds);
</script>
</body>
</html>