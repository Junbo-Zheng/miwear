#!/usr/bin/env python3
"""
Duplicate .bin File Finder
Scan specified path for all .bin files, find duplicates and generate report

Usage:
    python bincheck.py [PATH] [--ignore DIR1,DIR2] [--output REPORT.md]
    python bincheck.py . --ignore watchface,watchface_gl
    python bincheck.py /path/to/res --output duplicate_report.md
"""

import argparse
import hashlib
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


def calculate_file_hash(filepath: str, chunk_size: int = 8192) -> str:
    md5_hash = hashlib.md5()

    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except (IOError, OSError) as e:
        print(f"Warning: Unable to read file {filepath}: {e}", file=sys.stderr)
        return ""


def format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def scan_bin_files(
    root_path: str, ignore_dirs: Set[str]
) -> Tuple[Dict[str, List[Tuple[str, int]]], int, int]:
    hash_to_files: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
    total_files = 0
    total_size = 0

    root = Path(root_path).resolve()

    print(f"Scanning directory: {root}")
    if ignore_dirs:
        print(f"Ignoring directories: {', '.join(sorted(ignore_dirs))}")
    print()

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        for filename in filenames:
            if filename.endswith(".bin"):
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

    print(f"Scan complete! Found {total_files} .bin files" + " " * 20)

    return hash_to_files, total_files, total_size


def find_duplicates(
    hash_to_files: Dict[str, List[Tuple[str, int]]],
) -> Dict[str, Tuple[List[str], int]]:
    duplicates = {}

    for file_hash, files in hash_to_files.items():
        if len(files) > 1:
            file_paths = [f[0] for f in files]
            file_size = files[0][1]
            duplicates[file_hash] = (file_paths, file_size)

    return duplicates


def generate_report(
    duplicates: Dict[str, Tuple[List[str], int]],
    total_files: int,
    total_size: int,
    root_path: str,
    ignore_dirs: Set[str],
    output_file: Optional[str] = None,
) -> str:
    lines = []

    lines.append("# Duplicate .bin File Report")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Scanned Path**: `{root_path}`")

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
            f"| {idx} | {format_size(file_size)} | {len(file_paths)} | "
            f"{format_size(wasted)} | `{file_hash[:16]}...` |"
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


def main():
    parser = argparse.ArgumentParser(
        description="Scan and find duplicate .bin files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Scan current directory
  %(prog)s /path/to/res                       # Scan specified directory
  %(prog)s . --ignore watchface,watchface_gl  # Ignore specific directories
  %(prog)s . --output report.md               # Specify output filename
  %(prog)s . --ignore-dir watchface           # Use long option to ignore directory
        """,
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory)",
    )

    parser.add_argument(
        "-i",
        "--ignore",
        metavar="DIRS",
        help="Directory names to ignore, comma-separated (e.g., watchface,watchface_gl)",
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
        default="duplicate_bins_report.md",
        help="Output report filename (default: duplicate_bins_report.md)",
    )

    parser.add_argument(
        "--no-output",
        action="store_true",
        help="Do not save report file, only output to console",
    )

    args = parser.parse_args()

    if not os.path.isdir(args.path):
        print(
            f"Error: Path does not exist or is not a directory: {args.path}",
            file=sys.stderr,
        )
        sys.exit(1)

    ignore_dirs: Set[str] = set()

    if args.ignore:
        ignore_dirs.update(d.strip() for d in args.ignore.split(",") if d.strip())

    if args.ignore_dir:
        ignore_dirs.update(args.ignore_dir)

    print("=" * 60)
    print("Duplicate .bin File Detector")
    print("=" * 60)
    print()

    hash_to_files, total_files, total_size = scan_bin_files(args.path, ignore_dirs)

    print("\nAnalyzing duplicate files...")
    duplicates = find_duplicates(hash_to_files)

    print("\nGenerating report...")
    output_file: Optional[str] = None if args.no_output else args.output
    generate_report(
        duplicates,
        total_files,
        total_size,
        os.path.abspath(args.path),
        ignore_dirs,
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
    else:
        print("✅ No duplicate files found!")

    print("=" * 60)


if __name__ == "__main__":
    main()
