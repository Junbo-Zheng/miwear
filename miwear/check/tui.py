#!/usr/bin/env python3
# -*- coding:UTF-8 -*-
#
# Copyright (C) 2026 Junbo Zheng. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Terminal UI helpers for interactive single-select menus."""

import sys
from typing import Callable, Dict, List, Optional, Tuple

# ANSI colors
_CYAN_BG = "\033[46;30m"  # cyan background, black text
_RESET = "\033[0m"


def interactive_select(
    items: List[str],
    prompt: str,
    default_index: int = 0,
    format_item: Optional[Callable[[int, str], str]] = None,
) -> int:
    """Shared interactive single-select menu.

    Draws a list of items with arrow-key navigation and returns the
    index of the selected item.

    Args:
        items: list of display strings
        prompt: header text shown above the list
        default_index: initially highlighted item
        format_item: optional callback ``(index, name) -> display_str``;
            when *None* the raw item string is used
    """
    cursor = default_index
    total_lines = len(items) + 2  # prompt + blank + items

    def _build_lines():
        lines = [prompt, ""]
        for i, name in enumerate(items):
            mark = "*" if i == cursor else " "
            arrow = ">" if i == cursor else " "
            display = format_item(i, name) if format_item else name
            line = f"  {arrow} [{mark}] {display}"
            if i == cursor:
                line = f"{_CYAN_BG}{line}{_RESET}"
            lines.append(line)
        return lines

    def _draw(first_time=False):
        out = ""
        if not first_time:
            out += f"\033[{total_lines}A"
        for line in _build_lines():
            out += f"\r\033[K{line}\n"
        sys.stdout.write(out)
        sys.stdout.flush()

    _draw(first_time=True)

    try:
        import tty
        import termios

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setraw(fd)
        try:
            while True:
                ch = sys.stdin.read(1)
                if ch == "\r":
                    break
                if ch in ("\x03", "\x04", "\x18"):  # Ctrl+C, Ctrl+D, Ctrl+X
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    print("\n\nAborted.")
                    sys.exit(130)
                if ch == "\x1b":
                    seq = sys.stdin.read(2)
                    if seq == "[A" and cursor > 0:
                        cursor -= 1
                        _draw()
                    elif seq == "[B" and cursor < len(items) - 1:
                        cursor += 1
                        _draw()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
        pass

    print()
    return cursor


def select_view_variants(variants: Dict[str, Tuple[int, int]]) -> str:
    """Interactive single-select menu for view variant.

    Returns the chosen variant key (e.g. "view/res_480_480").
    """
    items = list(variants.keys())
    # Default: variant with the most files
    default = max(range(len(items)), key=lambda i: variants[items[i]][1])

    def _fmt(i: int, name: str) -> str:
        apps, files = variants[name]
        return f"{name:<12} ({apps} apps, {files:,} files)"

    idx = interactive_select(
        items,
        prompt="Select view variant to scan (\u2191\u2193 move, Enter confirm):",
        default_index=default,
        format_item=_fmt,
    )
    chosen = items[idx]
    print(f"Scanning: {chosen}")
    print()
    return chosen


def confirm_open_browser() -> bool:
    """Ask user whether to open HTML report in browser. Default: Yes."""
    items = ["Yes", "No"]
    idx = interactive_select(
        items,
        prompt="Open report in browser?",
        default_index=0,
    )
    return idx == 0
