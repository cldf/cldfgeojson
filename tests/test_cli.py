from cldfbench.__main__ import main


def test_webmercator(fixtures_dir, tmp_path):
    o = tmp_path / 'web.tif'
    main(['geojson.webmercator', str(fixtures_dir / 'geo.tif'), str(o)])
    assert o.exists()

    o = tmp_path / 'web.jpg'
    main(['geojson.webmercator', str(fixtures_dir / 'geo.tif'), str(o)])
    assert o.exists()


def test_overlay(fixtures_dir, tmp_path):
    o = tmp_path / 'web.html'
    main(['geojson.overlay', str(fixtures_dir / 'geo.tif'), '--out', str(o), '--test'])
    assert o.exists()

    o = tmp_path / 'web.jpg'
    main(['geojson.webmercator', str(fixtures_dir / 'geo.tif'), str(o)])
    oo = tmp_path / 'web.html'
    main(['geojson.overlay', str(o), '--out', str(oo), '--test'])
    assert oo.exists()
