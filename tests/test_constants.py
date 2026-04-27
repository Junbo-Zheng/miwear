"""Tests for miwear.constants module."""

from miwear.constants import APP_ID_TO_NAME, APP_NAME_TO_ID


def test_app_name_to_id_not_empty() -> None:
    assert len(APP_NAME_TO_ID) > 0


def test_reverse_mapping_consistent() -> None:
    for name, app_id in APP_NAME_TO_ID.items():
        assert APP_ID_TO_NAME[app_id] == name


def test_known_entries() -> None:
    assert APP_NAME_TO_ID["LAUNCHER"] == 0x0001
    assert APP_NAME_TO_ID["WATCHFACE"] == 0x0002
    assert APP_NAME_TO_ID["OFFLOAD"] == 0x1000
    assert APP_ID_TO_NAME[0x0000] == "NONE"


def test_no_duplicate_ids() -> None:
    ids = list(APP_NAME_TO_ID.values())
    assert len(ids) == len(set(ids)), "Duplicate app IDs found"
