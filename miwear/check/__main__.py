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

"""CLI entry point for the resource check tool."""

import argparse
import os
import sys
from typing import Optional, Set

from miwear.check.scanner import (
    detect_view_variants,
    execute_delete_action,
    find_duplicates,
    find_unused_resources,
    format_size,
    parse_extensions,
    parse_ignore_dirs,
    parse_prefixes,
    scan_files_for_diff,
    scan_files_for_duplicates,
    scan_resource_files,
)
from miwear.check.tui import confirm_open_browser, select_view_variants
from miwear.check.report import (
    generate_combined_report,
    generate_diff_report,
    generate_dup_report,
    generate_dup_report_html,
    generate_unused_report,
    generate_unused_report_html,
)


def run_dup_mode(args):
    """Run duplicate files detection mode"""
    if not os.path.isdir(args.dir):
        print(
            f"Error: Path does not exist or is not a directory: {args.dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    ignore_dirs = parse_ignore_dirs(args)
    extensions = parse_extensions(args)
    prefixes = parse_prefixes(args)

    # Auto-detect view variants when user hasn't manually specified ignores
    if not ignore_dirs:
        variants = detect_view_variants(args.dir, ignore_dirs, extensions)
        if variants:
            print()
            print("Detected multiple view variants across applications:")
            print()
            chosen = select_view_variants(variants)
            # Ignore all view variant dirs, then un-ignore the chosen one
            all_view_dirs = {k.split("/")[0] for k in variants}
            chosen_view_dir = chosen.split("/")[0]
            chosen_res_dir = chosen.split("/")[1]
            # Ignore other view dirs entirely
            for vd in all_view_dirs:
                if vd != chosen_view_dir:
                    ignore_dirs.add(vd)
            # For the chosen view dir, ignore sibling res dirs
            sibling_res = {
                k.split("/")[1]
                for k in variants
                if k.split("/")[0] == chosen_view_dir
                and k.split("/")[1] != chosen_res_dir
            }
            ignore_dirs.update(sibling_res)

    print("=" * 60)
    print("Duplicate File Detector")
    print("=" * 60)
    print()

    hash_to_files, total_files, total_size = scan_files_for_duplicates(
        args.dir, ignore_dirs, extensions, prefixes
    )

    print("\nAnalyzing duplicate files...")
    duplicates = find_duplicates(hash_to_files)

    if not duplicates:
        print("No duplicate files found!")
        sys.exit(0)

    print(f"Found {len(duplicates)} groups of duplicate files")

    if args.action == "delete":
        execute_delete_action(args.dir, duplicates)
    else:
        print("\nNo action specified. Use --action delete to remove duplicate files.")

    print("\nGenerating report...")
    output_file = None if args.no_output else args.output
    html_file = None
    if output_file:
        report_args = (
            duplicates,
            total_files,
            total_size,
            os.path.abspath(args.dir),
            ignore_dirs,
            extensions,
            prefixes,
        )
        generate_dup_report(*report_args, output_file)
        html_file = (
            output_file[:-3] if output_file.endswith(".md") else output_file
        ) + ".html"
        generate_dup_report_html(*report_args, html_file)

    print("\n" + "=" * 60)
    print("Scan Results Summary")
    print("=" * 60)
    print(f"Total files scanned: {total_files:,}")
    print(f"Total size scanned: {format_size(total_size)}")

    if duplicates:
        duplicate_count = sum(len(files) for files, _ in duplicates.values())
        wasted_size = sum(
            size * (len(files) - 1) for files, size in duplicates.values()
        )
        print(f"Duplicate groups: {len(duplicates):,}")
        print(f"Total duplicate files: {duplicate_count:,}")
        print(f"Wasted space: {format_size(wasted_size)}")

    print("=" * 60)

    if html_file and os.path.isfile(html_file):
        if confirm_open_browser():
            import webbrowser

            webbrowser.open(f"file://{os.path.abspath(html_file)}")


def run_unused_mode(args):
    """Run unused resources detection mode.

    Supports two usage patterns:
    1. Separate paths: -c ./code -d ./res (traditional)
    2. Combined path: -d ./applications (code and resources colocated)
       When view variants are detected, prompts user to select one.
       Code is scanned from -d, resources from the chosen view variant.
    """
    if not os.path.isdir(args.dir):
        print(f"Error: Resource path does not exist: {args.dir}", file=sys.stderr)
        sys.exit(1)

    ignore_dirs = parse_ignore_dirs(args)
    extensions = parse_extensions(args)
    if not extensions:
        extensions = {".bin"}

    code_path = args.code
    resource_path = args.dir

    # Auto-detect view variants to filter resource scan scope
    if not ignore_dirs:
        variants = detect_view_variants(args.dir, ignore_dirs, extensions)
        if variants:
            print()
            print("Detected multiple view variants:")
            print()
            chosen = select_view_variants(variants)
            # Build ignore list: ignore all view variant dirs except chosen
            all_view_dirs = {k.split("/")[0] for k in variants}
            chosen_view_dir = chosen.split("/")[0]
            chosen_res_dir = chosen.split("/")[1]
            for vd in all_view_dirs:
                if vd != chosen_view_dir:
                    ignore_dirs.add(vd)
            sibling_res = {
                k.split("/")[1]
                for k in variants
                if k.split("/")[0] == chosen_view_dir
                and k.split("/")[1] != chosen_res_dir
            }
            ignore_dirs.update(sibling_res)
            # If -c not specified, use -d as code path too
            if not code_path:
                code_path = args.dir

    if not code_path:
        print(
            "Error: --code is required for unused mode "
            "(no view variants detected for auto-detection)",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.isdir(code_path):
        print(f"Error: Code path does not exist: {code_path}", file=sys.stderr)
        sys.exit(1)

    file_extensions: Set[str] = set(
        ext.strip() if ext.strip().startswith(".") else f".{ext.strip()}"
        for ext in args.code_ext.split(",")
    )

    ext_desc = ", ".join(sorted(extensions))
    print("=" * 60)
    print(f"Unused Resource File Detector ({ext_desc})")
    print("=" * 60)
    print(f"Code path: {os.path.abspath(code_path)}")
    print(f"Resource path: {os.path.abspath(resource_path)}")
    if ignore_dirs:
        print(f"Ignoring: {', '.join(sorted(ignore_dirs))}")
    print()

    bin_files = scan_resource_files(resource_path, ignore_dirs, extensions)

    print()
    print("Analyzing unused resources...")
    unused_files, matched = find_unused_resources(
        bin_files, code_path, ignore_dirs, file_extensions, extensions
    )

    print()
    print("Generating report...")
    total_size = sum(size for _, size in bin_files.values())
    output_file: Optional[str] = None if args.no_output else args.output
    html_file = None
    if output_file:
        generate_unused_report(
            unused_files,
            len(bin_files),
            total_size,
            os.path.abspath(code_path),
            os.path.abspath(resource_path),
            ignore_dirs,
            extensions,
            output_file,
        )
        html_file = (
            output_file[:-3] if output_file.endswith(".md") else output_file
        ) + ".html"
        generate_unused_report_html(
            unused_files,
            len(bin_files),
            total_size,
            os.path.abspath(code_path),
            os.path.abspath(resource_path),
            ignore_dirs,
            extensions,
            html_file,
        )

    print()
    print("=" * 60)
    print("Scan Results Summary")
    print("=" * 60)
    print(f"Total resource files: {len(bin_files):,}")
    print(f"Total resource size: {format_size(total_size)}")
    print(f"Matched resources: {len(bin_files) - len(unused_files):,}")
    print(f"Unused files: {len(unused_files):,}")

    if unused_files:
        unused_size = sum(size for _, size in unused_files.values())
        print(f"Unused size: {format_size(unused_size)}")
        if len(bin_files) > 0:
            percent = (len(unused_files) / len(bin_files)) * 100
            print(f"Unused percentage: {percent:.1f}%")
    else:
        print("✅ All resource files are referenced!")

    print("=" * 60)

    if html_file and os.path.isfile(html_file):
        if confirm_open_browser():
            import webbrowser

            webbrowser.open(f"file://{os.path.abspath(html_file)}")


def run_both_mode(args):
    """Run both duplicate and unused checks"""
    print("=" * 60)
    print("Resource Check Tool - Full Analysis")
    print("=" * 60)
    print()

    # Step 1: Run dup check
    print("Step 1: Checking for duplicate files...")
    print("-" * 60)

    if not os.path.isdir(args.dir):
        print(
            f"Error: Path does not exist or is not a directory: {args.dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    ignore_dirs = parse_ignore_dirs(args)
    extensions = parse_extensions(args)
    prefixes = parse_prefixes(args)
    resource_exts = extensions if extensions else {".bin"}

    hash_to_files, total_files, total_size = scan_files_for_duplicates(
        args.dir, ignore_dirs, extensions, prefixes
    )

    print("\nAnalyzing duplicate files...")
    duplicates = find_duplicates(hash_to_files)

    dup_count = len(duplicates)
    if dup_count > 0:
        duplicate_file_count = sum(len(files) for files, _ in duplicates.values())
        wasted_size = sum(
            size * (len(files) - 1) for files, size in duplicates.values()
        )
        print(
            f"Found {dup_count} groups of duplicate files ({duplicate_file_count} files total)"
        )
        print(f"Wasted space: {format_size(wasted_size)}")
    else:
        print("No duplicate files found!")

    # Step 2: Run unused check (if code and resource paths provided)
    unused_files = {}
    bin_files = {}

    if args.code:
        print()
        print("-" * 60)
        print("Step 2: Checking for unused resources...")
        print("-" * 60)

        if not os.path.isdir(args.code):
            print(f"Warning: Code path does not exist: {args.code}", file=sys.stderr)
        else:
            file_extensions: Set[str] = set(
                ext.strip() if ext.strip().startswith(".") else f".{ext.strip()}"
                for ext in args.code_ext.split(",")
            )

            bin_files = scan_resource_files(args.dir, ignore_dirs, resource_exts)
            print()
            print("Analyzing unused resources...")
            unused_files, matched = find_unused_resources(
                bin_files, args.code, ignore_dirs, file_extensions, resource_exts
            )

            if unused_files:
                unused_size = sum(size for _, size in unused_files.values())
                print(f"Found {len(unused_files)} unused resource files")
                print(f"Unused size: {format_size(unused_size)}")
            else:
                print("✅ All resource files are referenced!")
    else:
        print()
        print("-" * 60)
        print("Step 2: Skipped (no --code path specified)")
        print("-" * 60)

    # Step 3: Generate combined report
    print()
    print("=" * 60)
    print("Generating combined report...")
    print("=" * 60)

    output_file = None if args.no_output else args.output
    generate_combined_report(
        duplicates,
        unused_files,
        total_files,
        total_size,
        len(bin_files),
        sum(size for _, size in bin_files.values()) if bin_files else 0,
        os.path.abspath(args.dir),
        os.path.abspath(args.code) if args.code else "",
        os.path.abspath(args.dir),
        ignore_dirs,
        extensions,
        prefixes,
        output_file,
    )

    # Step 4: Print summary
    print()
    print("=" * 60)
    print("Full Analysis Summary")
    print("=" * 60)
    print(f"Total files scanned: {total_files:,}")
    print(f"Total size scanned: {format_size(total_size)}")

    if duplicates:
        duplicate_count = sum(len(files) for files, _ in duplicates.values())
        wasted_size = sum(
            size * (len(files) - 1) for files, size in duplicates.values()
        )
        print(f"Duplicate groups: {len(duplicates):,}")
        print(f"Total duplicate files: {duplicate_count:,}")
        print(f"Wasted space: {format_size(wasted_size)}")

    if bin_files:
        print()
        print(f"Resource files: {len(bin_files):,}")
        print(
            f"Resource size: {format_size(sum(size for _, size in bin_files.values()))}"
        )
        if unused_files:
            unused_size = sum(size for _, size in unused_files.values())
            print(f"Unused files: {len(unused_files):,}")
            print(f"Unused size: {format_size(unused_size)}")

    print("=" * 60)


def run_diff_mode(args):
    """Run diff mode to compare two directories."""
    if not args.path1:
        print("Error: --path1 is required for diff mode", file=sys.stderr)
        sys.exit(1)

    if not args.path2:
        print("Error: --path2 is required for diff mode", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.path1):
        print(f"Error: Path1 does not exist: {args.path1}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.path2):
        print(f"Error: Path2 does not exist: {args.path2}", file=sys.stderr)
        sys.exit(1)

    ignore_dirs = parse_ignore_dirs(args)

    path1_abs = os.path.abspath(args.path1)
    path2_abs = os.path.abspath(args.path2)

    print("=" * 60)
    print("Directory Comparison Tool (Diff Mode)")
    print("=" * 60)
    print(f"Path1: {path1_abs}")
    print(f"Path2: {path2_abs}")
    if ignore_dirs:
        print(f"Ignoring directories: {', '.join(sorted(ignore_dirs))}")
    print()

    files1, dir_stats1 = scan_files_for_diff(args.path1, ignore_dirs)
    files2, dir_stats2 = scan_files_for_diff(args.path2, ignore_dirs)

    print(f"Found {len(files1)} unique files in {args.path1}")
    print(f"Found {len(files2)} unique files in {args.path2}")
    print()

    if args.sort == "count":
        sorted_dirs1 = sorted(dir_stats1.items(), key=lambda x: x[1], reverse=True)
        sorted_dirs2 = sorted(dir_stats2.items(), key=lambda x: x[1], reverse=True)
    else:
        sorted_dirs1 = sorted(dir_stats1.items())
        sorted_dirs2 = sorted(dir_stats2.items())

    print(f"--- {args.path1} File Count by Directory ---")
    for dir_path, count in sorted_dirs1:
        print(f"  {dir_path or '.':<60} {count}")
    print()

    print(f"--- {args.path2} File Count by Directory ---")
    for dir_path, count in sorted_dirs2:
        print(f"  {dir_path or '.':<60} {count}")
    print()

    keys1 = set(files1.keys())
    keys2 = set(files2.keys())

    only_in_path1 = keys1 - keys2
    only_in_path2 = keys2 - keys1
    common_keys = keys1 & keys2

    print("=" * 60)
    print("Comparison Results")
    print("=" * 60)
    print(f"Files only in path1: {len(only_in_path1)}")
    print(f"Files only in path2: {len(only_in_path2)}")
    print(f"Common files: {len(common_keys)}")
    print()

    if only_in_path1:
        print(f"--- Files only in {args.path1} ---")
        for key in sorted(only_in_path1):
            path1_info = files1[key]
            print(f"  {path1_info[0]}")
        print()

    if only_in_path2:
        print(f"--- Files only in {args.path2} ---")
        for key in sorted(only_in_path2):
            path2_info = files2[key]
            print(f"  {path2_info[0]}")
        print()

    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total files in {args.path1}: {len(files1)}")
    print(f"Total files in {args.path2}: {len(files2)}")
    print(f"Missing in {args.path2}: {len(only_in_path1)}")
    print(f"Extra in {args.path2}: {len(only_in_path2)}")
    print(f"Common files: {len(common_keys)}")

    if len(only_in_path1) > 0 or len(only_in_path2) > 0:
        print()
        print("❌ Differences found!")
    else:
        print()
        print("✅ All files match!")

    print("=" * 60)

    print("\nGenerating report...")
    output_file = None if args.no_output else args.output
    generate_diff_report(
        files1,
        files2,
        only_in_path1,
        only_in_path2,
        common_keys,
        dir_stats1,
        dir_stats2,
        path1_abs,
        path2_abs,
        ignore_dirs,
        output_file,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Resource Check Tool - Find duplicate files and unused resources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Mode Description:
  dup     - Find duplicate files by content hash (default)
  unused  - Find resources not referenced in code (default: .bin)
  both    - Run both dup + unused checks in one command
  diff    - Compare two directories and find missing/extra files

Examples:

  1. Find duplicate files (dup mode, default):

    %(prog)s -d ./resources -e bin
    %(prog)s -d ./resources -e bin png
    %(prog)s -d ./resources -e bin --action delete
    %(prog)s -d ./resources -e bin -p theme_ config_

  2. Find duplicate files with directory ignore:

    %(prog)s -d ./resources -e bin -i .git,node_modules
    %(prog)s -d ./project -e bin png -i po,view_65,view_66,view_67

  3. Auto view variant detection (dup and unused modes):

    When scanning a directory containing view/view_XX sub-directories
    with res* sub-directories (e.g., view/res_480_480, view_65/res),
    the tool automatically detects these variants and prompts a
    single-select menu. Default selection is the variant with the
    most files. This is skipped when -i is manually specified.

    %(prog)s -d ./project -e bin png

  4. Find unused resources (unused mode):

    -d sets where to find resource files (.bin etc).
    -c sets where to search code references (defaults to -d if omitted).

    %(prog)s -m unused -d ./project -e bin
    %(prog)s -m unused -d ./project -e bin --code-ext ".c,.h,.cpp,.java"
    %(prog)s -m unused -d ./project -c ./project/ota -e bin

  5. Run both checks (both mode):

    %(prog)s -m both -d ./resources -c ./code -e bin

  6. Compare two directories (diff mode):

    %(prog)s -m diff --path1 ./design --path2 ./converted
    %(prog)s -m diff --path1 ./design/icons --path2 ./converted/icons
    %(prog)s -m diff --path1 ./design --path2 ./converted --sort count
    %(prog)s -m diff --path1 ./design --path2 ./converted -i .git,__pycache__

  7. Output control:

    Reports are generated in both Markdown and HTML formats.
    After generation, you will be prompted to open the HTML
    report in your browser.

    %(prog)s -d ./resources -e bin -o my_report.md
    %(prog)s -d ./resources -e bin --no-output
        """,
    )

    # Mode selection
    parser.add_argument(
        "-m",
        "--mode",
        choices=["dup", "unused", "both", "diff"],
        default="dup",
        help="Operation mode: dup (find duplicates), unused (find unused resources), "
        "both (run both), diff (compare two directories) (default: dup)",
    )

    # Common arguments
    parser.add_argument(
        "-d",
        "--dir",
        metavar="PATH",
        default=".",
        help="Directory to scan for resource files (.bin etc) in unused mode, "
        "or for duplicate files in dup mode. (default: '.')",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        metavar="DIRS",
        help="Directory names to ignore, comma-separated",
    )
    parser.add_argument(
        "--ignore-dir",
        action="append",
        metavar="DIR",
        help="Directory name to ignore (can be used multiple times)",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default="resource_check_report.md",
        help="Output report filename (default: resource_check_report.md)",
    )
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="Do not save report file",
    )

    # Duplicate detection arguments
    parser.add_argument(
        "-e",
        "--ext",
        action="extend",
        nargs="+",
        metavar="EXT",
        help="File extensions to scan (e.g., -e bin png or -e bin,png). "
        "In unused mode defaults to .bin if not specified",
    )
    parser.add_argument(
        "-p",
        "--prefix",
        action="extend",
        nargs="+",
        metavar="PREFIX",
        help="File name prefix to scan (e.g., --prefix theme_ config_) "
        "OR path prefix mapping for unused mode "
        "(format: code_prefix:resource_prefix)",
    )
    parser.add_argument(
        "-a",
        "--action",
        metavar="ACTION",
        choices=["delete"],
        help="Action to execute for duplicates (only 'delete' supported)",
    )

    # Unused resources arguments
    parser.add_argument(
        "-c",
        "--code",
        metavar="PATH",
        help="Directory to search for code references in unused mode. "
        "If omitted, defaults to -d (search code in the same directory "
        "as resources). Use this to narrow the code search scope, e.g. "
        "-d ./applications -c ./applications/ota",
    )
    parser.add_argument(
        "--code-ext",
        metavar="EXTS",
        default=".c,.h,.cpp,.hpp,.cc,.cxx,.py,.java,.js,.ts,.json",
        help="Code file extensions to scan when searching for resource "
        "references in unused mode (comma-separated, "
        "default: .c,.h,.cpp,.hpp,.cc,.cxx,.py,.java,.js,.ts,.json)",
    )

    parser.add_argument(
        "--path1",
        metavar="PATH",
        help="First directory for diff mode (source, e.g., design folder with PNG files)",
    )
    parser.add_argument(
        "--path2",
        metavar="PATH",
        help="Second directory for diff mode (target, e.g., rgb888 folder with bin files)",
    )
    parser.add_argument(
        "--sort",
        choices=["alpha", "count"],
        default="alpha",
        help="Sort directory listing by alpha (alphabetical) or count (by file count, default: alpha)",
    )

    args = parser.parse_args()

    # Execute based on mode
    if args.mode == "dup":
        run_dup_mode(args)
    elif args.mode == "unused":
        run_unused_mode(args)
    elif args.mode == "both":
        run_both_mode(args)
    elif args.mode == "diff":
        run_diff_mode(args)


if __name__ == "__main__":
    main()
