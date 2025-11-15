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
import gzip
import argparse
import sys
import re

try:
    from miwear import __version__
except ImportError:
    __version__ = "0.0.1"


def is_gz_not_targz(filename):
    return filename.endswith(".gz") and not filename.endswith(".tar.gz")


def natural_sort_key(filename):
    filename = os.path.basename(filename)
    parts = re.split(r"(\d+)", filename)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def get_sorted_gz_files(directory):
    gz_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if is_gz_not_targz(file):
                gz_files.append(os.path.join(root, file))

    gz_files.sort(key=natural_sort_key)
    return gz_files


def run(directory, log_file, output_file):
    gz_files = get_sorted_gz_files(directory)

    if not gz_files:
        print(f"Not found .gz files in {directory}")
        return

    print("Found the following files and processing them in order:")
    for i, file_path in enumerate(gz_files, 1):
        print(f"{i}. {os.path.basename(file_path)}")

    with open(output_file, "wb") as merged_file:
        for gz_file_path in gz_files:
            try:
                with gzip.open(gz_file_path, "rb") as f_in:
                    decompressed_data = f_in.read()
                merged_file.write(decompressed_data)
                print(
                    f"File {os.path.basename(gz_file_path)} decompressed and merged successfully......"
                )
            except Exception as e:
                print(f"Error processing file {gz_file_path}: {e}")

        if os.path.isfile(log_file):
            try:
                with open(log_file, "rb") as tmp_log:
                    merged_file.write(tmp_log.read())
                print(f"file {log_file} merged successfully...")
            except Exception as e:
                print(f"Error merging log file {log_file}: {e}")
        else:
            print(f"Log file {log_file} does not exist, skipping")
    print(
        f"Successfully completed! All files have been merged in order into {output_file} ..."
    )


def main():
    parser = argparse.ArgumentParser(
        description="both .gz file and the log file will be unzip and merged"
    )
    parser.add_argument(
        "--version", action="store_true", help="Show miwear_gz version and exit."
    )

    parser.add_argument(
        "--log_file",
        type=str,
        default="tmp.log",
        help="specify the log file to be merged, tmp.log is used by default",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="output.log",
        help="specify the name of the output file, output.log is used by default",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="specify the directory to search, current directory by default",
    )

    args = parser.parse_args()
    if args.version:
        print(f"miwear_gz version: {__version__}")
        sys.exit(0)

    run(args.path, args.log_file, args.output_file)


if __name__ == "__main__":
    main()
