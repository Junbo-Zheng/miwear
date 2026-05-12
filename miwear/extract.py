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

import glob
import zipfile
import argparse
import os
from typing import List

try:
    from miwear import __version__
except ImportError:
    __version__ = "0.0.1"


def select_interactive(items: List[str]) -> int:
    """Arrow-key inline selector. Returns chosen index."""
    import sys
    import tty
    import termios
    import shutil

    cur = 0
    total = len(items)
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    out = sys.stdout
    cols = shutil.get_terminal_size().columns

    def display_lines() -> int:
        """Calculate total display lines considering wrapping."""
        count = 0
        for item in items:
            line_len = len(item) + 2  # ">" or " " + space + item
            count += max(1, (line_len + cols - 1) // cols)
        return count

    def render(first: bool = False) -> None:
        lines = display_lines()
        if not first:
            out.write(f"\033[{lines}A")
        for i, item in enumerate(items):
            if i == cur:
                out.write(f"\033[1;32m> {item}\033[0m\033[K\n")
            else:
                out.write(f"  {item}\033[K\n")
        out.flush()

    def readkey() -> bytes:
        ch = os.read(fd, 1)
        if ch == b"\x1b":
            ch += os.read(fd, 1)
            ch += os.read(fd, 1)
        return ch

    try:
        tty.setcbreak(fd)
        out.write("\033[?25l")
        out.flush()
        render(first=True)
        while True:
            key = readkey()
            if key in (b"\r", b"\n"):
                break
            elif key == b"\x1b[A" and cur > 0:
                cur -= 1
            elif key == b"\x1b[B" and cur < total - 1:
                cur += 1
            elif key == b"\x03":
                raise KeyboardInterrupt
            else:
                continue
            render()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        out.write("\033[?25h")
        out.flush()

    return cur


def find_zip_file(path: str) -> str:
    """Find a zip file in the given directory. Prompt user if multiple."""
    zip_files = sorted(glob.glob(os.path.join(path, "*.zip")))
    if not zip_files:
        print(f"No ZIP files found in '{os.path.abspath(path)}'.")
        raise SystemExit(1)
    if len(zip_files) == 1:
        print(f"Found: {os.path.basename(zip_files[0])}")
        return zip_files[0]

    names = [os.path.basename(f) for f in zip_files]
    print(f"Found {len(zip_files)} ZIP files (↑↓ to select, Enter to confirm):")
    idx = select_interactive(names)
    print(f"Selected: {names[idx]}")
    return zip_files[idx]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract files with specific extensions from a ZIP archive "
        "into the current directory."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "zipfile",
        type=str,
        nargs="?",
        default=None,
        help="Path to the ZIP file (auto-detects in current directory if omitted)",
    )
    parser.add_argument(
        "-e",
        "--ext",
        type=str,
        nargs="+",
        default=["elf"],
        help="File extensions to extract (default: elf)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=".",
        help="Output directory (default: current directory)",
    )

    args = parser.parse_args()

    if args.zipfile is None:
        args.zipfile = find_zip_file(".")
    elif not os.path.isfile(args.zipfile):
        print(f"Error: '{args.zipfile}' does not exist or is not a file.")
        return

    # Normalize extensions (strip leading dots)
    extensions: List[str] = [ext.lstrip(".").lower() for ext in args.ext]

    try:
        with zipfile.ZipFile(args.zipfile, "r") as zf:
            matched = [
                name
                for name in zf.namelist()
                if not name.endswith("/")
                and name.rsplit(".", 1)[-1].lower() in extensions
            ]

            if not matched:
                print(
                    f"No files with extension(s) "
                    f"{', '.join('.' + e for e in extensions)} "
                    f"found in '{args.zipfile}'."
                )
                return

            os.makedirs(args.output, exist_ok=True)

            print(
                f"Extracting {len(matched)} file(s) with extension(s) "
                f"{', '.join('.' + e for e in extensions)} "
                f"to '{os.path.abspath(args.output)}':"
            )

            for name in matched:
                basename = os.path.basename(name)
                target = os.path.join(args.output, basename)
                with zf.open(name) as src, open(target, "wb") as dst:
                    dst.write(src.read())
                print(f"  {basename}")

            print("Done!")

    except zipfile.BadZipFile:
        print(f"Error: '{args.zipfile}' is not a valid ZIP file.")
    except PermissionError:
        print(f"Error: Permission denied for '{args.zipfile}'.")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
