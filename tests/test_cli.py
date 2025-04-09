from cldfbench.__main__ import main


def test_validate(fixtures_dir, capsys):
    main(['geojson.validate', str(fixtures_dir / 'dataset')])
    out, _ = capsys.readouterr()
    assert 'bare1276' in out


def test_geojson(fixtures_dir, capsys):
    main(['--no-config', 'geojson.geojson', str(fixtures_dir / 'dataset'), 'bare1276', '--glottolog', '-'])
    out, _ = capsys.readouterr()
    assert 'FeatureCollection' in out

    main([
        'geojson.geojson',
        str(fixtures_dir / 'dataset'),
        '--glottolog', str(fixtures_dir / 'glottolog'), 'mand1448'])
    out, _ = capsys.readouterr()
    assert 'Point' in out

    main([
        'geojson.geojson',
        str(fixtures_dir / 'dataset'),
        '--dataset2', str(fixtures_dir / 'dataset'),
        '--glottolog', str(fixtures_dir / 'glottolog'),
        '--no-glottolog',
        'abcd1236'])
    out, _ = capsys.readouterr()
    assert 'Point' not in out


def test_compare(fixtures_dir, capsys):
    main([
        'geojson.compare',
        str(fixtures_dir / 'dataset'),
        str(fixtures_dir / 'dataset'),
    ])
    out, _ = capsys.readouterr()
    assert 'abcd1236' in out


def test_multipolygon_spread(fixtures_dir, capsys):
    main([
        'geojson.multipolygon_spread',
        str(fixtures_dir / 'dataset'),
        '--threshold', '0'])
    out, _ = capsys.readouterr()
    assert 'bare1276' in out


def test_glottolog_distance(fixtures_dir, capsys):
    main([
        'geojson.glottolog_distance',
        str(fixtures_dir / 'dataset'),
        '--glottolog', str(fixtures_dir / 'glottolog')])
    out, _ = capsys.readouterr()
    assert 'mand1448' in out


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
