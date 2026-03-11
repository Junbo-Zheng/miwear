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

"""
Resource Check Tool - Unified resource management
Features: Find duplicate files + Find unused resources

Usage:
    # Find duplicate files (default mode)
    python check.py -d ./res -e bin
    python check.py -d ./res -e bin --action delete

    # Find unused resources
    python check.py --mode unused -c ./apps -r ./res

    # Run both checks
    python check.py --mode both -d ./res -c ./apps -r ./res -e bin
"""

import argparse
import hashlib
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


# ============ Common Utility Functions ============


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def parse_ignore_dirs(args) -> Set[str]:
    """Parse ignore directory arguments"""
    ignore_dirs: Set[str] = set()
    if args.ignore:
        ignore_dirs.update(d.strip() for d in args.ignore.split(",") if d.strip())
    if args.ignore_dir:
        ignore_dirs.update(args.ignore_dir)
    return ignore_dirs


def parse_extensions(args) -> Set[str]:
    """Parse file extension arguments"""
    extensions: Set[str] = set()
    if args.ext:
        for ext in args.ext:
            if "," in ext:
                for e in ext.split(","):
                    e = e.strip()
                    if e:
                        extensions.add(e if e.startswith(".") else f".{e}")
            else:
                extensions.add(ext if ext.startswith(".") else f".{ext}")
    return extensions


def parse_prefixes(args) -> Set[str]:
    """Parse file prefix arguments"""
    prefixes: Set[str] = set()
    if args.prefix:
        for prefix in args.prefix:
            if "," in prefix:
                for p in prefix.split(","):
                    p = p.strip()
                    if p:
                        prefixes.add(p)
            else:
                prefixes.add(prefix)
    return prefixes


# ============ Duplicate Files Functions ============


def calculate_file_hash(filepath: str, chunk_size: int = 8192) -> str:
    """Calculate MD5 hash of a file"""
    md5_hash = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except (IOError, OSError) as e:
        print(f"Warning: Unable to read file {filepath}: {e}", file=sys.stderr)
        return ""


def should_include_file(
    filename: str, extensions: Set[str], prefixes: Set[str]
) -> bool:
    """Check if file should be included based on extension and prefix filters"""
    has_ext_match = not extensions
    has_prefix_match = not prefixes

    if extensions:
        for ext in extensions:
            if filename.endswith(ext):
                has_ext_match = True
                break

    if prefixes:
        for prefix in prefixes:
            if filename.startswith(prefix):
                has_prefix_match = True
                break

    if extensions and prefixes:
        return has_ext_match and has_prefix_match
    elif extensions:
        return has_ext_match
    elif prefixes:
        return has_prefix_match
    else:
        return True


def scan_files_for_duplicates(
    root_path: str,
    ignore_dirs: Set[str],
    extensions: Set[str],
    prefixes: Set[str],
) -> Tuple[Dict[str, List[Tuple[str, int]]], int, int]:
    """Scan files and calculate hash values"""
    hash_to_files: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
    total_files = 0
    total_size = 0
    root = Path(root_path).resolve()

    print(f"Scanning directory: {root}")
    if ignore_dirs:
        print(f"Ignoring directories: {', '.join(sorted(ignore_dirs))}")

    filter_info = []
    if extensions:
        filter_info.append(f"extensions: {', '.join(sorted(extensions))}")
    if prefixes:
        filter_info.append(f"prefixes: {', '.join(sorted(prefixes))}")
    if filter_info:
        print(f"Filtering by {', '.join(filter_info)}")
    print()

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        for filename in filenames:
            if should_include_file(filename, extensions, prefixes):
                filepath = os.path.join(dirpath, filename)
                total_files += 1

                if total_files % 500 == 0:
                    print(f"Scanned {total_files} files...", end="\r")

                try:
                    file_size = os.path.getsize(filepath)
                    total_size += file_size
                    file_hash = calculate_file_hash(filepath)

                    if file_hash:
                        rel_path = os.path.relpath(filepath, root)
                        hash_to_files[file_hash].append((rel_path, file_size))
                except OSError as e:
                    print(
                        f"\nWarning: Unable to access file {filepath}: {e}",
                        file=sys.stderr,
                    )

    filter_desc = "filtered files"
    if extensions:
        filter_desc += f" with extensions {', '.join(extensions)}"
    if prefixes:
        filter_desc += f" with prefixes {', '.join(prefixes)}"

    print(f"Scan complete! Found {total_files} {filter_desc}" + " " * 20)
    return hash_to_files, total_files, total_size


def find_duplicates(
    hash_to_files: Dict[str, List[Tuple[str, int]]],
) -> Dict[str, Tuple[List[str], int]]:
    """Find duplicate files"""
    duplicates = {}
    for file_hash, files in hash_to_files.items():
        if len(files) > 1:
            file_paths = [f[0] for f in files]
            file_size = files[0][1]
            duplicates[file_hash] = (file_paths, file_size)
    return duplicates


def execute_delete_action(
    root_path: str, duplicates: Dict[str, Tuple[List[str], int]]
) -> bool:
    """Execute delete action for duplicate files"""
    print(f"\nDeleting duplicate files from {len(duplicates)} groups...")

    deleted_count = 0
    total_freed_size = 0
    root = Path(root_path).resolve()

    for file_hash, (file_paths, file_size) in duplicates.items():
        if len(file_paths) > 1:
            for path in file_paths[1:]:
                try:
                    filepath = root / path
                    actual_size = os.path.getsize(filepath)
                    os.remove(filepath)
                    deleted_count += 1
                    total_freed_size += actual_size
                    print(f"Deleted: {path} ({format_size(actual_size)})")
                except OSError as e:
                    print(f"Error deleting {path}: {e}", file=sys.stderr)

    print(f"\nDeleted {deleted_count} files")
    print(f"Freed space: {format_size(total_freed_size)}")
    return True


def generate_dup_report(
    duplicates: Dict[str, Tuple[List[str], int]],
    total_files: int,
    total_size: int,
    root_path: str,
    ignore_dirs: Set[str],
    extensions: Set[str],
    prefixes: Set[str],
    output_file: str | None = None,
) -> str:
    """Generate duplicate files report"""
    lines = []
    lines.append("# Duplicate File Report")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Scanned Path**: `{root_path}`")

    if ignore_dirs:
        lines.append(
            f"**Ignored Directories**: {', '.join(f'`{d}`' for d in sorted(ignore_dirs))}"
        )
    if extensions:
        lines.append(f"**File Extensions**: {', '.join(sorted(extensions))}")
    if prefixes:
        lines.append(f"**File Prefixes**: {', '.join(sorted(prefixes))}")

    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 📊 Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Files Scanned | {total_files:,} |")
    lines.append(f"| Total Size Scanned | {format_size(total_size)} |")

    duplicate_count = sum(len(files) for files, _ in duplicates.values())
    duplicate_groups = len(duplicates)
    wasted_size = sum(size * (len(files) - 1) for files, size in duplicates.values())

    lines.append(f"| Duplicate Groups | {duplicate_groups:,} |")
    lines.append(f"| Total Duplicate Files | {duplicate_count:,} |")
    lines.append(f"| Wasted Space | {format_size(wasted_size)} |")
    lines.append("")

    if not duplicates:
        lines.append("---")
        lines.append("")
        lines.append("✅ **No duplicate files found!**")
        report = "\n".join(lines)
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\nReport saved to: {output_file}")
        return report

    sorted_duplicates = sorted(duplicates.items(), key=lambda x: x[1][1], reverse=True)

    dir_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"count": 0, "size": 0})
    for file_hash, (file_paths, file_size) in duplicates.items():
        for path in file_paths:
            dir_path = os.path.dirname(path)
            if not dir_path:
                dir_path = "."
            dir_stats[dir_path]["count"] += 1
            dir_stats[dir_path]["size"] += file_size

    lines.append("---")
    lines.append("")
    lines.append("## 📁 Duplicate Files by Directory")
    lines.append("")
    lines.append("| Directory | Duplicate Files | Total Size |")
    lines.append("|-----------|-----------------|------------|")

    sorted_dirs = sorted(dir_stats.items(), key=lambda x: x[1]["size"], reverse=True)
    for dir_path, stats in sorted_dirs:
        lines.append(
            f"| `{dir_path}` | {stats['count']} | {format_size(stats['size'])} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📋 Duplicate Details")
    lines.append("")
    lines.append(
        f"Found **{duplicate_groups}** groups of duplicate files (sorted by file size):"
    )
    lines.append("")

    for idx, (file_hash, (file_paths, file_size)) in enumerate(sorted_duplicates, 1):
        lines.append(f"### Group {idx} - File Size: {format_size(file_size)}")
        lines.append("")
        lines.append(
            f"The following **{len(file_paths)}** files have identical content:"
        )
        lines.append("")
        for path in sorted(file_paths):
            lines.append(f"- `{path}`")
        lines.append("")
        lines.append(
            f"> 💡 Deleting {len(file_paths) - 1} of them can save {format_size(file_size * (len(file_paths) - 1))}"
        )
        lines.append("")
        lines.append(f"MD5: `{file_hash}`")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## 📈 Summary Table")
    lines.append("")
    lines.append("| # | File Size | Duplicates | Wasted Space | MD5 Hash |")
    lines.append("|---|-----------|------------|--------------|----------|")

    for idx, (file_hash, (file_paths, file_size)) in enumerate(sorted_duplicates, 1):
        wasted = file_size * (len(file_paths) - 1)
        lines.append(
            f"| {idx} | {format_size(file_size)} | {len(file_paths)} | {format_size(wasted)} | `{file_hash[:16]}...` |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Report generated*")

    report = "\n".join(lines)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nReport saved to: {output_file}")
    return report


# ============ Unused Resources Functions ============

# Conservative matching: require filename stem to appear in a
# string-literal context (quoted, path-separated, or as a format
# pattern).  Short stems (<=3 chars) demand stricter evidence to
# avoid false positives from common variable/function names.

MIN_STEM_LENGTH_FOR_LOOSE_MATCH = 4


def scan_bin_files(
    resource_path: str, ignore_dirs: Set[str]
) -> Dict[str, Tuple[str, int]]:
    """Scan all .bin files in resource directory"""
    bin_files: Dict[str, Tuple[str, int]] = {}
    root = Path(resource_path).resolve()

    print(f"Scanning resource directory: {root}")

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        for filename in filenames:
            if filename.endswith(".bin"):
                filepath = os.path.join(dirpath, filename)
                try:
                    file_size = os.path.getsize(filepath)
                    rel_path = os.path.relpath(filepath, root)
                    bin_files[rel_path] = (filepath, file_size)
                except OSError as e:
                    print(
                        f"Warning: Cannot access file {filepath}: {e}", file=sys.stderr
                    )

    print(f"Found {len(bin_files)} .bin files in resource directory")
    return bin_files


def _is_referenced_in_content(stem: str, content: str) -> bool:
    """Check if a resource file stem is referenced in code content.

    Uses conservative matching strategy:
    - High confidence: "stem.bin", '/stem', stem.bin in any quote context
    - Medium confidence: /stem%, "stem" in quotes, stem as path component
    - Short stems (<=3 chars): require exact quoted or path match
    - Numbered stems (e.g. anim0): also try base name with format specifier
    """

    # High confidence: exact filename with .bin extension
    if f"{stem}.bin" in content:
        return True

    # High confidence: path separator + stem (e.g. /reminder, /fail)
    if f"/{stem}" in content:
        return True

    # Medium confidence: quoted stem (e.g. "reminder", 'fail')
    if f'"{stem}"' in content or f"'{stem}'" in content:
        return True

    # Numbered stem: anim0 -> check for "anim%d", "anim%s", "anim%02d" etc.
    # Strips trailing digits: anim0->anim, frame01->frame, icon123->icon
    base_stem = re.sub(r"\d+$", "", stem)
    if base_stem and base_stem != stem:
        if re.search(rf'["\'/]{re.escape(base_stem)}%[dsx0-9]', content):
            return True

    # Short stems need stricter matching - stop here
    if len(stem) < MIN_STEM_LENGTH_FOR_LOOSE_MATCH:
        return False

    # Medium confidence: stem followed by format specifier
    # Catches: "anim%d.bin", "icon%s", "frame%02d"
    if re.search(rf'"{re.escape(stem)}%[dsx0-9]', content):
        return True

    # Medium confidence: stem in a string with .bin nearby
    # Catches: snprintf(path, "%s/fail.%s", dir, "bin")
    if (
        re.search(rf'["\'][^"\']*{re.escape(stem)}[^"\']*["\']', content)
        and ".bin" in content
    ):
        return True

    return False


def find_unused_resources(
    bin_files: Dict[str, Tuple[str, int]],
    code_path: str,
    ignore_dirs: Set[str],
    file_extensions: Set[str],
) -> Tuple[Dict[str, Tuple[str, int]], Dict[str, str]]:
    """Find unused resources using conservative filename-based matching.

    For each .bin resource file, extract the stem (filename without .bin)
    and search code files for references to that stem in string-literal
    contexts.
    """

    # Build stem -> [resource_paths] mapping
    stem_to_paths: Dict[str, List[str]] = defaultdict(list)
    for bin_path in bin_files:
        basename = os.path.basename(bin_path)
        stem = os.path.splitext(basename)[0]
        stem_to_paths[stem].append(bin_path)

    referenced_files: Set[str] = set()
    match_details: Dict[str, str] = {}
    unmatched_stems = set(stem_to_paths.keys())

    root = Path(code_path).resolve()
    print(f"Scanning code directory: {root}")

    file_count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        if not unmatched_stems:
            break

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in file_extensions:
                continue

            filepath = os.path.join(dirpath, filename)
            file_count += 1

            if file_count % 100 == 0:
                print(f"Scanned {file_count} code files...", end="\r")

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except (IOError, OSError):
                continue

            newly_matched = []
            for stem in unmatched_stems:
                if _is_referenced_in_content(stem, content):
                    for bin_path in stem_to_paths[stem]:
                        referenced_files.add(bin_path)
                    rel_code = os.path.relpath(filepath, root)
                    match_details[stem] = rel_code
                    newly_matched.append(stem)

            for stem in newly_matched:
                unmatched_stems.discard(stem)

    print(
        f"Scanned {file_count} code files, matched {len(referenced_files)} "
        f"resource files" + " " * 20
    )

    unused_files = {
        path: info for path, info in bin_files.items() if path not in referenced_files
    }

    return unused_files, match_details


def generate_unused_report(
    unused_files: Dict[str, Tuple[str, int]],
    total_files: int,
    total_size: int,
    code_path: str,
    resource_path: str,
    ignore_dirs: Set[str],
    output_file: Optional[str] = None,
) -> str:
    """Generate unused resources report"""
    lines = []

    lines.append("# Unused .bin Resource File Report")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Code Path**: `{code_path}`")
    lines.append(f"**Resource Path**: `{resource_path}`")

    if ignore_dirs:
        lines.append(
            f"**Ignored Directories**: {', '.join(f'`{d}`' for d in sorted(ignore_dirs))}"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 📊 Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Resource Files | {total_files:,} |")
    lines.append(f"| Total Resource Size | {format_size(total_size)} |")

    unused_count = len(unused_files)
    unused_size = sum(size for _, size in unused_files.values())

    lines.append(f"| Unused Files | {unused_count:,} |")
    lines.append(f"| Unused Size | {format_size(unused_size)} |")

    if total_files > 0:
        unused_percent = (unused_count / total_files) * 100
        lines.append(f"| Unused Percentage | {unused_percent:.1f}% |")

    lines.append("")

    if not unused_files:
        lines.append("---")
        lines.append("")
        lines.append("✅ **All resource files are referenced in code!**")
        report = "\n".join(lines)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\nReport saved to: {output_file}")

        return report

    sorted_unused = sorted(unused_files.items(), key=lambda x: x[1][1], reverse=True)

    dir_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"count": 0, "size": 0})
    for path, (_, size) in unused_files.items():
        dir_path = os.path.dirname(path)
        if not dir_path:
            dir_path = "."
        dir_stats[dir_path]["count"] += 1
        dir_stats[dir_path]["size"] += size

    lines.append("---")
    lines.append("")
    lines.append("## 📁 Unused Files by Directory")
    lines.append("")
    lines.append("| Directory | Unused Files | Total Size |")
    lines.append("|-----------|--------------|------------|")

    sorted_dirs = sorted(dir_stats.items(), key=lambda x: x[1]["size"], reverse=True)
    for dir_path, stats in sorted_dirs:
        lines.append(
            f"| `{dir_path}` | {stats['count']} | {format_size(stats['size'])} |"
        )

    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📋 Unused Files Detail")
    lines.append("")
    lines.append(f"Found **{unused_count}** unused .bin files (sorted by size):")
    lines.append("")

    for idx, (path, (_, size)) in enumerate(sorted_unused, 1):
        lines.append(f"{idx}. `{path}` ({format_size(size)})")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📈 Top 50 Largest Unused Files")
    lines.append("")
    lines.append("| # | File Path | Size |")
    lines.append("|---|-----------|------|")

    for idx, (path, (_, size)) in enumerate(sorted_unused[:50], 1):
        lines.append(f"| {idx} | `{path}` | {format_size(size)} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Report generated*")

    report = "\n".join(lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nReport saved to: {output_file}")

    return report


def parse_prefix_mapping(mapping_str: str) -> Tuple[str, str]:
    """Parse prefix mapping string like '/resource/app:/rgb888/app'"""
    parts = mapping_str.split(":", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return mapping_str.strip(), ""


# ============ Mode Execution Functions ============


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
    generate_dup_report(
        duplicates,
        total_files,
        total_size,
        os.path.abspath(args.dir),
        ignore_dirs,
        extensions,
        prefixes,
        output_file,
    )

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


def run_unused_mode(args):
    """Run unused resources detection mode"""
    if not os.path.isdir(args.code):
        print(f"Error: Code path does not exist: {args.code}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.resource):
        print(f"Error: Resource path does not exist: {args.resource}", file=sys.stderr)
        sys.exit(1)

    ignore_dirs = parse_ignore_dirs(args)

    file_extensions: Set[str] = set(
        ext.strip() if ext.strip().startswith(".") else f".{ext.strip()}"
        for ext in args.code_ext.split(",")
    )

    print("=" * 60)
    print("Unused .bin Resource File Detector")
    print("=" * 60)
    print()

    bin_files = scan_bin_files(args.resource, ignore_dirs)

    print()
    print("Analyzing unused resources...")
    unused_files, matched = find_unused_resources(
        bin_files, args.code, ignore_dirs, file_extensions
    )

    print()
    print("Generating report...")
    total_size = sum(size for _, size in bin_files.values())
    output_file: Optional[str] = None if args.no_output else args.output
    generate_unused_report(
        unused_files,
        len(bin_files),
        total_size,
        os.path.abspath(args.code),
        os.path.abspath(args.resource),
        ignore_dirs,
        output_file,
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

    if args.code and args.resource:
        print()
        print("-" * 60)
        print("Step 2: Checking for unused resources...")
        print("-" * 60)

        if not os.path.isdir(args.code):
            print(f"Warning: Code path does not exist: {args.code}", file=sys.stderr)
        elif not os.path.isdir(args.resource):
            print(
                f"Warning: Resource path does not exist: {args.resource}",
                file=sys.stderr,
            )
        else:
            file_extensions: Set[str] = set(
                ext.strip() if ext.strip().startswith(".") else f".{ext.strip()}"
                for ext in args.code_ext.split(",")
            )

            bin_files = scan_bin_files(args.resource, ignore_dirs)
            print()
            print("Analyzing unused resources...")
            unused_files, matched = find_unused_resources(
                bin_files, args.code, ignore_dirs, file_extensions
            )

            if unused_files:
                unused_size = sum(size for _, size in unused_files.values())
                print(f"Found {len(unused_files)} unused .bin files")
                print(f"Unused size: {format_size(unused_size)}")
            else:
                print("✅ All resource files are referenced!")
    else:
        print()
        print("-" * 60)
        print("Step 2: Skipped (no --code and --resource paths specified)")
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
        os.path.abspath(args.resource) if args.resource else "",
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


def generate_combined_report(
    duplicates: Dict[str, Tuple[List[str], int]],
    unused_files: Dict[str, Tuple[str, int]],
    total_files: int,
    total_size: int,
    resource_files: int,
    resource_size: int,
    scan_path: str,
    code_path: str,
    resource_path: str,
    ignore_dirs: Set[str],
    extensions: Set[str],
    prefixes: Set[str],
    output_file: Optional[str] = None,
) -> str:
    """Generate combined report"""
    lines = []

    lines.append("# Resource Check Report - Full Analysis")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Scanned Path**: `{scan_path}`")

    if code_path:
        lines.append(f"**Code Path**: `{code_path}`")
    if resource_path:
        lines.append(f"**Resource Path**: `{resource_path}`")

    if ignore_dirs:
        lines.append(
            f"**Ignored Directories**: {', '.join(f'`{d}`' for d in sorted(ignore_dirs))}"
        )
    if extensions:
        lines.append(f"**File Extensions**: {', '.join(sorted(extensions))}")
    if prefixes:
        lines.append(f"**File Prefixes**: {', '.join(sorted(prefixes))}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Overall summary
    lines.append("## 📊 Overall Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Files Scanned | {total_files:,} |")
    lines.append(f"| Total Size Scanned | {format_size(total_size)} |")

    if duplicates:
        duplicate_count = sum(len(files) for files, _ in duplicates.values())
        wasted_size = sum(
            size * (len(files) - 1) for files, size in duplicates.values()
        )
        lines.append(f"| Duplicate Groups | {len(duplicates):,} |")
        lines.append(f"| Total Duplicate Files | {duplicate_count:,} |")
        lines.append(f"| Wasted Space (Duplicates) | {format_size(wasted_size)} |")

    if resource_files > 0:
        lines.append(f"| Resource Files | {resource_files:,} |")
        lines.append(f"| Resource Size | {format_size(resource_size)} |")

        if unused_files:
            unused_size = sum(size for _, size in unused_files.values())
            lines.append(f"| Unused Files | {len(unused_files):,} |")
            lines.append(f"| Unused Size | {format_size(unused_size)} |")

    lines.append("")

    # Duplicate files section
    lines.append("---")
    lines.append("")
    lines.append("## 🔍 Duplicate Files Analysis")
    lines.append("")

    if not duplicates:
        lines.append("✅ **No duplicate files found!**")
    else:
        duplicate_count = sum(len(files) for files, _ in duplicates.values())
        wasted_size = sum(
            size * (len(files) - 1) for files, size in duplicates.values()
        )

        lines.append(f"Found **{len(duplicates)}** groups of duplicate files:")
        lines.append("")
        lines.append(f"- Total duplicate files: {duplicate_count:,}")
        lines.append(f"- Wasted space: {format_size(wasted_size)}")
        lines.append("")

        sorted_duplicates = sorted(
            duplicates.items(), key=lambda x: x[1][1], reverse=True
        )

        lines.append("### Top 10 Largest Duplicate Groups")
        lines.append("")
        lines.append("| # | File Size | Duplicates | Wasted Space |")
        lines.append("|---|-----------|------------|--------------|")

        for idx, (file_hash, (file_paths, file_size)) in enumerate(
            sorted_duplicates[:10], 1
        ):
            wasted = file_size * (len(file_paths) - 1)
            lines.append(
                f"| {idx} | {format_size(file_size)} | {len(file_paths)} | {format_size(wasted)} |"
            )

        lines.append("")

    # Unused resources section
    if resource_files > 0:
        lines.append("---")
        lines.append("")
        lines.append("## 🗑️ Unused Resources Analysis")
        lines.append("")

        if not unused_files:
            lines.append("✅ **All resource files are referenced in code!**")
        else:
            unused_size = sum(size for _, size in unused_files.values())

            lines.append(f"Found **{len(unused_files)}** unused .bin files:")
            lines.append("")
            lines.append(f"- Unused size: {format_size(unused_size)}")
            if resource_files > 0:
                percent = (len(unused_files) / resource_files) * 100
                lines.append(f"- Unused percentage: {percent:.1f}%")
            lines.append("")

            sorted_unused = sorted(
                unused_files.items(), key=lambda x: x[1][1], reverse=True
            )

            lines.append("### Top 10 Largest Unused Files")
            lines.append("")
            lines.append("| # | File Path | Size |")
            lines.append("|---|-----------|------|")

            for idx, (path, (_, size)) in enumerate(sorted_unused[:10], 1):
                lines.append(f"| {idx} | `{path}` | {format_size(size)} |")

            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Report generated by check.py*")

    report = "\n".join(lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nReport saved to: {output_file}")

    return report


# ============ Main Entry Point ============


def main():
    parser = argparse.ArgumentParser(
        description="Resource Check Tool - Find duplicate files and unused resources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find duplicate files (default mode)
  %(prog)s -d ./res -e bin
  %(prog)s -d ./res -e bin --action delete
  
  # Find unused resources
  %(prog)s --mode unused -c ./apps -r ./res
  %(prog)s --mode unused -c ./apps -r ./res --prefix "/resource/app:"
  
  # Run both checks
  %(prog)s --mode both -d ./res -c ./apps -r ./res -e bin

Mode Description:
  dup     - Find duplicate files by content hash
  unused  - Find .bin resources not referenced in code
  both    - Run both checks in one command
        """,
    )

    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["dup", "unused", "both"],
        default="dup",
        help="Operation mode: dup (find duplicates), unused (find unused resources), both (run both) (default: dup)",
    )

    # Common arguments
    parser.add_argument(
        "-d",
        "--dir",
        metavar="PATH",
        default=".",
        help="Root directory to scan for duplicates (default: current directory)",
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
        help="File extension to scan for duplicates (e.g., --ext .bin .png or --ext .bin,.png)",
    )
    parser.add_argument(
        "-p",
        "--prefix",
        action="extend",
        nargs="+",
        metavar="PREFIX",
        help="File name prefix to scan (e.g., --prefix theme_ config_) OR path prefix mapping for unused mode (format: code_prefix:resource_prefix)",
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
        help="Code directory to scan for .bin references (required for unused/both mode)",
    )
    parser.add_argument(
        "-r",
        "--resource",
        metavar="PATH",
        help="Resource directory containing .bin files (required for unused/both mode)",
    )
    parser.add_argument(
        "--code-ext",
        metavar="EXTS",
        default=".c,.h,.cpp,.hpp,.cc,.cxx,.py,.java,.js,.ts,.json",
        help="Code file extensions to scan for references (comma-separated, default: .c,.h,.cpp,.hpp,.cc,.cxx,.py,.java,.js,.ts,.json)",
    )

    args = parser.parse_args()

    # Validate arguments based on mode
    if args.mode == "unused":
        if not args.code:
            print("Error: --code is required for unused mode", file=sys.stderr)
            sys.exit(1)
        if not args.resource:
            print("Error: --resource is required for unused mode", file=sys.stderr)
            sys.exit(1)

    # Execute based on mode
    if args.mode == "dup":
        run_dup_mode(args)
    elif args.mode == "unused":
        run_unused_mode(args)
    elif args.mode == "both":
        run_both_mode(args)


if __name__ == "__main__":
    main()
