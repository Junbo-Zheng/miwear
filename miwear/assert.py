#!/usr/bin/env python3
# -*- coding:UTF-8 -*-
#
# Copyright (C) 2024 Junbo Zheng. All rights reserved.
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

import argparse
import os
import sys

try:
    from miwear import __version__
except ImportError:
    __version__ = "0.0.1"


def run(
    input_file_path, output_file_path, start_line_number=None, end_line_number=None
):
    if not os.path.exists(input_file_path):
        print(f"Error: Input file '{input_file_path}' does not exist.")
        sys.exit(1)

    if os.path.exists(output_file_path):
        print(f"'{output_file_path}' already exit, remove")
        os.remove(output_file_path)

    if start_line_number is not None and end_line_number is not None:
        if end_line_number < start_line_number:
            print("Error: End line number cannot be smaller than start line number.")
            sys.exit(1)

    with open(input_file_path, "r") as file:
        text = file.read()

    lines = text.split("\n")

    if start_line_number is not None and end_line_number is not None:
        lines = lines[start_line_number : end_line_number + 1]

    start_keyword = "Assertion failed panic"
    start_line = next(i for i, line in enumerate(lines) if start_keyword in line) + 1

    end_keyword = "PID GROUP PRI POLICY"
    end_line = next(i for i, line in enumerate(lines) if end_keyword in line) - 1

    filtered_lines = lines[start_line : end_line + 1]

    with open(output_file_path, "w") as file:
        for line in filtered_lines:
            file.write(line + "\n")

    print(f"Filtered lines have been written to {output_file_path}")


def main():
    arg_parser = argparse.ArgumentParser(
        description="parse log to extract assert information"
    )

    arg_parser.add_argument(
        "--version",
        action="store_true",
        help="Show miwear_assert version and exit.",
    )

    arg_parser.add_argument(
        "-i", "--input_file", type=str, default="mi.log", help="input file"
    )
    arg_parser.add_argument(
        "-o",
        "--output_file",
        type=str,
        nargs="?",
        default="log.txt",
        help="output file",
    )
    arg_parser.add_argument(
        "-s", "--start_line", type=int, nargs="?", help="start line number"
    )
    arg_parser.add_argument(
        "-e", "--end_line", type=int, nargs="?", help="end line number"
    )

    args = arg_parser.parse_args()
    if args.version:
        print(f"miwear_assert version: {__version__}")
        sys.exit(0)

    run(args.input_file, args.output_file, args.start_line, args.end_line)


if __name__ == "__main__":
    main()
