from pathlib import Path

import pytest
from django.conf import settings

from ..utils import walk_files


@pytest.fixture(autouse=True)
def data_dir_setup(tmp_path: Path):
    settings.DATA_DIR = tmp_path

    yield

    print(f"files in tmp_path {tmp_path}:")
    total = 0
    for path in walk_files(tmp_path):
        print(f"  {path}")
        total += 1
    print(f"total: {total} files")
