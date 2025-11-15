#!/usr/bin/env python3
# -*- coding:UTF-8 -*-
#
# Copyright (C) 2025 Junbo Zheng. All rights reserved.
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

import os
import glob
import subprocess
import argparse
import sys

try:
    from miwear import __version__
except ImportError:
    __version__ = "0.0.1"


def main():
    parser = argparse.ArgumentParser(
        description="Batch extract all ZIP files in the specified directory."
    )
    parser.add_argument(
        "--version", action="store_true", help="Show miwear_tz version and exit."
    )
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Specify the directory path to extract .tar.gz files (default: current directory)",
    )

    args = parser.parse_args()
    if args.version:
        print(f"miwear_tz version: {__version__}")
        sys.exit(0)

    # Check if the specified path exists
    if not os.path.exists(args.path):
        print(f"Error: The specified path '{args.path}' does not exist.")
        return

    # Use the specified path instead of current directory
    target_dir = os.path.abspath(args.path)
    tar_gz_files = glob.glob(os.path.join(target_dir, "*.tar.gz"))

    if not tar_gz_files:
        print(f"not found any .tar.gz files in '{target_dir}'")
        return

    print(f"found {len(tar_gz_files)} .tar.gz files in '{target_dir}'")

    for file_path in tar_gz_files:
        file_name = os.path.basename(file_path)
        print(f"extract: {file_name}")

        try:
            result = subprocess.run(
                ["tar", "-xzvf", file_path],
                cwd=target_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.stdout:
                print(result.stdout)
            print(f"extract success: {file_name}")

        except subprocess.CalledProcessError as e:
            if e.returncode == 2 and any(
                warning in e.stderr
                for warning in [
                    "Removing leading `/' from member names",
                    "decompression OK, trailing garbage ignored",
                ]
            ):
                print("extract success with warning, just ignored")
            else:
                print(f"✗ extract failed: {file_name}")
                print(f"error message: {e.stderr}")
                print(f"return code: {e.returncode}")


if __name__ == "__main__":
    main()
