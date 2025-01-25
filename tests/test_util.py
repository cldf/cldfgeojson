import pathlib

import pytest
from pycldf import Dataset

from cldfgeojson.util import speaker_area_shapes


@pytest.fixture
def dataset(fixtures_dir):
    return Dataset.from_metadata(fixtures_dir / "dataset"/ "Generic-metadata.json")


def test_speaker_area_shapes(dataset):
    assert speaker_area_shapes(dataset)
    assert speaker_area_shapes(dataset, fix_geometry=True)
