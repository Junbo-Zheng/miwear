"""Tests for miwear.loganalyzer module."""

from miwear.loganalyzer import AppIDAnalyzer, ScreenStateAnalyzer


def test_appid_parse_valid_line() -> None:
    analyzer = AppIDAnalyzer()
    line = "[01/02 04:23:33] [59] [ap] [pagemanager] on_ui_create: create view 0x18ac02b0:{15, 5}"
    entry = analyzer.parse_line(line)
    assert entry is not None
    assert entry.app_id == 15
    assert entry.page_id == 5
    assert entry.timestamp == "01/02 04:23:33"
    assert entry.app_name == "SPORTS"


def test_appid_parse_invalid_line() -> None:
    analyzer = AppIDAnalyzer()
    assert analyzer.parse_line("some random log line") is None
    assert analyzer.parse_line("") is None


def test_screen_state_parse_valid_line() -> None:
    analyzer = ScreenStateAnalyzer()
    line = (
        "[01/02 05:51:19] [59] [ap] [MiWearScreen]"
        " async_apply_screen_state_change: Screen state: ON-->OFF, source: TOUCH_PALM"
    )
    entry = analyzer.parse_line(line)
    assert entry is not None
    assert entry.from_state == "ON"
    assert entry.to_state == "OFF"
    assert entry.source == "TOUCH_PALM"
    assert entry.timestamp == "01/02 05:51:19"


def test_screen_state_parse_invalid_line() -> None:
    analyzer = ScreenStateAnalyzer()
    assert analyzer.parse_line("some random log line") is None


def test_appid_analyze_file(tmp_path) -> None:
    log_content = """[01/02 04:23:33] [59] [ap] [pagemanager] on_ui_create: create view 0x18ac02b0:{15, 5}
some other log line
[01/02 04:23:35] [59] [ap] [pagemanager] on_ui_create: create view 0x18ac02b0:{1, 0}
"""
    log_file = tmp_path / "test.log"
    log_file.write_text(log_content)

    analyzer = AppIDAnalyzer()
    entries = analyzer.analyze(str(log_file))
    assert len(entries) == 2
    assert entries[0].app_name == "SPORTS"
    assert entries[1].app_name == "LAUNCHER"
