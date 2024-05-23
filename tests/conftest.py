import pathlib

import pytest

from pycldf import Dataset


@pytest.fixture
def fixtures_dir():
    return pathlib.Path(__file__).parent / 'fixtures'


@pytest.fixture
def glottolog_cldf(fixtures_dir):
    return Dataset.from_metadata(fixtures_dir / 'gl-metadata.json')
