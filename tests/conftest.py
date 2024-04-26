import pathlib

import pytest

from pycldf import Dataset


@pytest.fixture
def glottolog_cldf():
    return Dataset.from_metadata(pathlib.Path(__file__).parent / 'fixtures' / 'gl-metadata.json')
