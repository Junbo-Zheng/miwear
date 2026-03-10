#!/usr/bin/env python3
"""
Unused .bin Resource File Finder
Scan code for .bin file references and find unused resources

Usage:
    python unused_bin.py --code /path/to/code --resource /path/to/res
    python unused_bin.py -c /path/to/code -r /path/to/res --output report.md
    python unused_bin.py -c /path/to/code -r /path/to/res --prefix "/resource/app:/rgb888/app"
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


def format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def scan_bin_files(
    resource_path: str, ignore_dirs: Set[str]
) -> Dict[str, Tuple[str, int]]:
    """
    Scan all .bin files in resource directory

    Returns:
        Dict mapping relative path -> (absolute path, file size)
    """
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


def scan_code_references(
    code_path: str, ignore_dirs: Set[str], file_extensions: Set[str]
) -> Set[str]:
    """
    Scan code files for .bin file references

    Returns:
        Set of referenced .bin file paths/names
    """
    references: Set[str] = set()
    root = Path(code_path).resolve()

    print(f"Scanning code directory: {root}")

    bin_pattern = re.compile(r'["\']([^"\']*\.bin)["\']')

    file_count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in file_extensions:
                filepath = os.path.join(dirpath, filename)
                file_count += 1

                if file_count % 100 == 0:
                    print(f"Scanned {file_count} code files...", end="\r")

                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        matches = bin_pattern.findall(content)
                        for match in matches:
                            references.add(match)
                except (IOError, OSError):
                    pass

    print(
        f"Scanned {file_count} code files, found {len(references)} unique .bin references"
        + " " * 20
    )
    return references


def normalize_path(path: str, prefix_mappings: List[Tuple[str, str]]) -> str:
    """
    Normalize a path reference from code to match resource file path

    Args:
        path: Path from code reference
        prefix_mappings: List of (code_prefix, resource_prefix) tuples
    """
    path = path.strip("/")

    for code_prefix, res_prefix in prefix_mappings:
        if path.startswith(code_prefix.strip("/")):
            path = path.replace(code_prefix.strip("/"), res_prefix.strip("/"), 1)
            break

    return path


def find_unused_resources(
    bin_files: Dict[str, Tuple[str, int]],
    code_references: Set[str],
    prefix_mappings: List[Tuple[str, str]],
) -> Tuple[Dict[str, Tuple[str, int]], Dict[str, List[str]]]:
    referenced_files: Set[str] = set()
    matched_references: Dict[str, List[str]] = defaultdict(list)

    bin_filenames: Dict[str, List[str]] = defaultdict(list)
    for bin_path in bin_files:
        filename = os.path.basename(bin_path)
        bin_filenames[filename].append(bin_path)

    for ref in code_references:
        normalized = normalize_path(ref, prefix_mappings)
        ref_filename = os.path.basename(normalized)

        if normalized in bin_files:
            referenced_files.add(normalized)
            matched_references[ref].append(normalized)
        elif ref_filename in bin_filenames:
            for bin_path in bin_filenames[ref_filename]:
                if bin_path.endswith(normalized) or normalized in bin_path:
                    referenced_files.add(bin_path)
                    matched_references[ref].append(bin_path)

    unused_files = {
        path: info for path, info in bin_files.items() if path not in referenced_files
    }

    return unused_files, dict(matched_references)


def generate_report(
    unused_files: Dict[str, Tuple[str, int]],
    total_files: int,
    total_size: int,
    code_path: str,
    resource_path: str,
    ignore_dirs: Set[str],
    output_file: Optional[str] = None,
) -> str:
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


def main():
    parser = argparse.ArgumentParser(
        description="Find unused .bin resource files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -c /path/to/code -r /path/to/res
  %(prog)s -c /path/to/apps -r /path/to/res/rgb888/app --output unused_report.md
  %(prog)s -c ./apps -r ./res/rgb888/app --prefix "/resource/app:"
  %(prog)s -c ./apps -r ./res/rgb888/system --prefix "/resource/system:"

Prefix Mapping:
  Use --prefix to map code references to resource paths.
  Format: "code_prefix:resource_prefix"
  Example: --prefix "/resource/app:" means code references starting with
           "/resource/app" will be matched against resource files directly.
        """,
    )

    parser.add_argument(
        "-c",
        "--code",
        required=True,
        metavar="PATH",
        help="Code directory to scan for .bin references",
    )

    parser.add_argument(
        "-r",
        "--resource",
        required=True,
        metavar="PATH",
        help="Resource directory containing .bin files",
    )

    parser.add_argument(
        "-i", "--ignore", metavar="DIRS", help="Directories to ignore (comma-separated)"
    )

    parser.add_argument(
        "--ignore-dir",
        action="append",
        metavar="DIR",
        help="Directory to ignore (can be used multiple times)",
    )

    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default="unused_bins_report.md",
        help="Output report filename (default: unused_bins_report.md)",
    )

    parser.add_argument(
        "--no-output",
        action="store_true",
        help="Do not save report file, only output to console",
    )

    parser.add_argument(
        "--prefix",
        action="append",
        metavar="MAPPING",
        help="Path prefix mapping (format: code_prefix:resource_prefix, can be used multiple times)",
    )

    parser.add_argument(
        "--ext",
        metavar="EXTS",
        default=".c,.h,.cpp,.hpp,.cc,.cxx,.py,.java,.js,.ts,.json",
        help="Code file extensions to scan (comma-separated, default: .c,.h,.cpp,.hpp,.cc,.cxx,.py,.java,.js,.ts,.json)",
    )

    args = parser.parse_args()

    if not os.path.isdir(args.code):
        print(f"Error: Code path does not exist: {args.code}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.resource):
        print(f"Error: Resource path does not exist: {args.resource}", file=sys.stderr)
        sys.exit(1)

    ignore_dirs: Set[str] = set()
    if args.ignore:
        ignore_dirs.update(d.strip() for d in args.ignore.split(",") if d.strip())
    if args.ignore_dir:
        ignore_dirs.update(args.ignore_dir)

    prefix_mappings: List[Tuple[str, str]] = []
    if args.prefix:
        for p in args.prefix:
            prefix_mappings.append(parse_prefix_mapping(p))

    file_extensions: Set[str] = set(
        ext.strip() if ext.strip().startswith(".") else f".{ext.strip()}"
        for ext in args.ext.split(",")
    )

    print("=" * 60)
    print("Unused .bin Resource File Detector")
    print("=" * 60)
    print()

    bin_files = scan_bin_files(args.resource, ignore_dirs)

    print()
    code_references = scan_code_references(args.code, ignore_dirs, file_extensions)

    print()
    print("Analyzing unused resources...")
    unused_files, matched = find_unused_resources(
        bin_files, code_references, prefix_mappings
    )

    print()
    print("Generating report...")
    total_size = sum(size for _, size in bin_files.values())
    output_file: Optional[str] = None if args.no_output else args.output
    generate_report(
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
    print(f"Code references found: {len(code_references):,}")
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


if __name__ == "__main__":
    main()
