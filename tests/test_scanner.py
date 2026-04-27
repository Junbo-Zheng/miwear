"""Tests for miwear.check.scanner module."""

import os
import tempfile

from miwear.check.scanner import (
    calculate_file_hash,
    extract_base_name,
    format_size,
    should_include_file,
)


def test_format_size() -> None:
    assert format_size(0) == "0.00 B"
    assert format_size(1023) == "1023.00 B"
    assert format_size(1024) == "1.00 KB"
    assert format_size(1024 * 1024) == "1.00 MB"


def test_should_include_file_no_filters() -> None:
    assert should_include_file("test.bin", set(), set()) is True


def test_should_include_file_ext_match() -> None:
    assert should_include_file("test.bin", {".bin"}, set()) is True
    assert should_include_file("test.png", {".bin"}, set()) is False


def test_should_include_file_prefix_match() -> None:
    assert should_include_file("theme_icon.bin", set(), {"theme_"}) is True
    assert should_include_file("icon.bin", set(), {"theme_"}) is False


def test_should_include_file_both_filters() -> None:
    assert should_include_file("theme_icon.bin", {".bin"}, {"theme_"}) is True
    assert should_include_file("theme_icon.png", {".bin"}, {"theme_"}) is False
    assert should_include_file("icon.bin", {".bin"}, {"theme_"}) is False


def test_extract_base_name() -> None:
    assert extract_base_name("confirm.indexed_8.png") == "confirm"
    assert extract_base_name("confirm.png") == "confirm"
    assert extract_base_name("icon.24.png") == "icon"
    assert extract_base_name("noext") == "noext"


def test_calculate_file_hash() -> None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(b"hello world")
        path = f.name
    try:
        h = calculate_file_hash(path)
        assert len(h) == 32  # MD5 hex digest length
        # Same content should produce same hash
        assert h == calculate_file_hash(path)
    finally:
        os.unlink(path)


def test_calculate_file_hash_identical_files() -> None:
    content = b"duplicate content"
    paths = []
    try:
        for _ in range(2):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
                f.write(content)
                paths.append(f.name)
        assert calculate_file_hash(paths[0]) == calculate_file_hash(paths[1])
    finally:
        for p in paths:
            os.unlink(p)


def test_calculate_file_hash_different_files() -> None:
    paths = []
    try:
        for i in range(2):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
                f.write(f"content {i}".encode())
                paths.append(f.name)
        assert calculate_file_hash(paths[0]) != calculate_file_hash(paths[1])
    finally:
        for p in paths:
            os.unlink(p)
