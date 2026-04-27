"""Tests for miwear.gz and miwear.targz modules."""

import gzip
import os
import tarfile
import tempfile

from miwear.gz import get_sorted_gz_files, is_gz_not_targz, natural_sort_key


def test_is_gz_not_targz() -> None:
    assert is_gz_not_targz("log.gz") is True
    assert is_gz_not_targz("log1.gz") is True
    assert is_gz_not_targz("log.tar.gz") is False
    assert is_gz_not_targz("log.txt") is False


def test_natural_sort_key() -> None:
    files = ["log10.gz", "log2.gz", "log1.gz", "log20.gz"]
    sorted_files = sorted(files, key=natural_sort_key)
    assert sorted_files == ["log1.gz", "log2.gz", "log10.gz", "log20.gz"]


def test_get_sorted_gz_files(tmp_path: "tempfile.TemporaryDirectory") -> None:
    # Create test .gz files
    for name in ["log2.gz", "log1.gz", "log10.gz"]:
        path = tmp_path / name
        with gzip.open(str(path), "wb") as f:
            f.write(b"test data")

    # Create a .tar.gz that should be excluded
    tar_path = tmp_path / "archive.tar.gz"
    with tarfile.open(str(tar_path), "w:gz"):
        pass  # empty tar

    result = get_sorted_gz_files(str(tmp_path))
    basenames = [os.path.basename(p) for p in result]
    assert basenames == ["log1.gz", "log2.gz", "log10.gz"]
