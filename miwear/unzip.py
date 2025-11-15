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

import glob
import zipfile
import argparse
import sys
import os

try:
    from miwear import __version__
except ImportError:
    __version__ = "0.0.1"


def main():
    parser = argparse.ArgumentParser(
        description="Batch extract all ZIP files in the specified directory."
    )
    parser.add_argument(
        "--version", action="store_true", help="Show miwear_uz version and exit."
    )
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Specify the directory path to extract ZIP files (default: current directory)",
    )

    args = parser.parse_args()
    if args.version:
        print(f"miwear_uz version: {__version__}")
        sys.exit(0)

    # Check if the specified path exists
    if not os.path.exists(args.path):
        print(f"Error: The specified path '{args.path}' does not exist.")
        return

    # Get all zip files in the specified directory
    zip_pattern = os.path.join(args.path, "*.zip")
    zip_files = glob.glob(zip_pattern)

    if not zip_files:
        print(f"No zip files found in '{args.path}'.")
        return

    print(f"Found {len(zip_files)} zip files in '{args.path}'. Extracting...")

    for zip_file in zip_files:
        print(f"Extracting: {zip_file}")
        try:
            with zipfile.ZipFile(zip_file, "r") as zf:
                zf.extractall(args.path)
        except zipfile.BadZipFile:
            print(f"  Error: {zip_file} is not a valid ZIP file")
        except PermissionError:
            print(f"  Error: Permission denied for {zip_file}")
        except Exception as e:
            print(f"  Extraction failed: {str(e)}")

    print("Extraction complete!")


if __name__ == "__main__":
    main()
