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
    python check.py --mode unused -c ./apps -d ./res

    # Run both checks
    python check.py --mode both -d ./res -c ./apps -e bin
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


# ============ View Variant Detection ============

VIEW_VARIANT_RE = re.compile(r"^view(_\d+)?$")
RES_DIR_RE = re.compile(r"^res")


def detect_view_variants(
    root_path: str, ignore_dirs: Set[str], extensions: Set[str]
) -> Dict[str, Tuple[int, int]]:
    """Detect view/res variant paths (view/res_480_480, view_65/res, ...).

    Scans for view variant directories, then looks one level deeper for
    res* sub-directories. Returns dict of "view_dir/res_dir" ->
    (app_count, file_count) only when 2+ variants exist.
    """
    variants: Dict[str, Set[str]] = defaultdict(set)
    file_counts: Dict[str, int] = defaultdict(int)

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for d in list(dirnames):
            if VIEW_VARIANT_RE.match(d):
                view_path = os.path.join(dirpath, d)
                app_name = os.path.relpath(dirpath, root_path)
                # Look one level deeper for res* directories
                try:
                    sub_dirs = [
                        s
                        for s in os.listdir(view_path)
                        if os.path.isdir(os.path.join(view_path, s))
                        and RES_DIR_RE.match(s)
                    ]
                except OSError:
                    continue
                for res_dir in sub_dirs:
                    key = f"{d}/{res_dir}"
                    variants[key].add(app_name)
                    res_path = os.path.join(view_path, res_dir)
                    for vdp, _, vfns in os.walk(res_path):
                        for fn in vfns:
                            if not extensions or any(
                                fn.endswith(e) for e in extensions
                            ):
                                file_counts[key] += 1
                # Prevent os.walk from descending into view dirs
                dirnames.remove(d)

    if len(variants) < 2:
        return {}
    return {v: (len(variants[v]), file_counts[v]) for v in sorted(variants)}


def select_view_variants(variants: Dict[str, Tuple[int, int]]) -> str:
    """Interactive single-select menu for view variant.

    Returns the chosen variant key (e.g. "view/res_480_480").
    """
    items = list(variants.keys())
    cursor = max(
        range(len(items)), key=lambda i: variants[items[i]][1]
    )  # default: most files
    total_lines = len(items) + 2  # header + blank + items

    # ANSI colors
    CYAN_BG = "\033[46;30m"  # cyan background, black text
    RESET = "\033[0m"

    def build_lines():
        lines = [
            "Select view variant to scan (\u2191\u2193 move, Enter confirm):",
            "",
        ]
        for i, name in enumerate(items):
            apps, files = variants[name]
            mark = "*" if i == cursor else " "
            arrow = ">" if i == cursor else " "
            line = f"  {arrow} [{mark}] {name:<12} ({apps} apps, {files:,} files)"
            if i == cursor:
                line = f"{CYAN_BG}{line}{RESET}"
            lines.append(line)
        return lines

    def draw(first_time=False):
        out = ""
        if not first_time:
            out += f"\033[{total_lines}A"
        for line in build_lines():
            out += f"\r\033[K{line}\n"
        sys.stdout.write(out)
        sys.stdout.flush()

    draw(first_time=True)

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
                        draw()
                    elif seq == "[B" and cursor < len(items) - 1:
                        cursor += 1
                        draw()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
        pass

    print()
    chosen = items[cursor]
    print(f"Scanning: {chosen}")
    print()
    return chosen


def confirm_open_browser() -> bool:
    """Ask user whether to open HTML report in browser. Default: Yes."""
    items = ["Yes", "No"]
    cursor = 0  # default: Yes
    total_lines = len(items) + 2

    CYAN_BG = "\033[46;30m"
    RESET = "\033[0m"

    def draw(first_time=False):
        out = ""
        if not first_time:
            out += f"\033[{total_lines}A"
        out += "\r\033[KOpen report in browser?\n\r\033[K\n"
        for i, name in enumerate(items):
            mark = "*" if i == cursor else " "
            arrow = ">" if i == cursor else " "
            line = f"  {arrow} [{mark}] {name}"
            if i == cursor:
                line = f"{CYAN_BG}{line}{RESET}"
            out += f"\r\033[K{line}\n"
        sys.stdout.write(out)
        sys.stdout.flush()

    draw(first_time=True)

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
                if ch in ("\x03", "\x04", "\x18"):
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    print()
                    return False
                if ch == "\x1b":
                    seq = sys.stdin.read(2)
                    if seq == "[A" and cursor > 0:
                        cursor -= 1
                        draw()
                    elif seq == "[B" and cursor < len(items) - 1:
                        cursor += 1
                        draw()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
        pass

    print()
    return cursor == 0


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

    return has_ext_match and has_prefix_match


def scan_files_for_duplicates(
    root_path: str,
    ignore_dirs: Set[str],
    extensions: Set[str],
    prefixes: Set[str],
) -> Tuple[Dict[str, List[Tuple[str, int]]], int, int]:
    """Scan files and calculate hash values.

    Uses a size-based pre-filter: only files sharing the same size are
    hashed, because files with unique sizes cannot be duplicates.
    """
    size_to_files: Dict[int, List[Tuple[str, str]]] = defaultdict(list)
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

    # Phase 1: collect files grouped by size
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        for filename in filenames:
            if should_include_file(filename, extensions, prefixes):
                filepath = os.path.join(dirpath, filename)
                total_files += 1

                if total_files % 500 == 0:
                    print(f"Scanned {total_files} files...", end="\r", flush=True)

                try:
                    file_size = os.path.getsize(filepath)
                    total_size += file_size
                    rel_path = os.path.relpath(filepath, root)
                    size_to_files[file_size].append((rel_path, filepath))
                except OSError as e:
                    print(
                        f"\nWarning: Unable to access file {filepath}: {e}",
                        file=sys.stderr,
                    )

    # Phase 2: only hash files whose size appears more than once
    hash_to_files: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
    hashed_count = 0
    for file_size, files in size_to_files.items():
        if len(files) < 2:
            continue
        for rel_path, filepath in files:
            file_hash = calculate_file_hash(filepath)
            if file_hash:
                hash_to_files[file_hash].append((rel_path, file_size))
            hashed_count += 1

    filter_desc = "filtered files"
    if extensions:
        filter_desc += f" with extensions {', '.join(extensions)}"
    if prefixes:
        filter_desc += f" with prefixes {', '.join(prefixes)}"

    print(
        f"Scan complete! Found {total_files} {filter_desc}, "
        f"hashed {hashed_count} candidates" + " " * 20
    )
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
    output_file: Optional[str] = None,
) -> str:
    """Generate duplicate files report"""
    lines = []
    lines.append("# Duplicate File Report")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Command**: `{' '.join(sys.argv)}`")
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


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Duplicate File Report</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    max-width:1400px;margin:0 auto;padding:20px;background:#f8f9fa;color:#333}}
h1{{color:#1a73e8;border-bottom:3px solid #1a73e8;padding-bottom:10px}}
h2{{color:#333;margin-top:30px}}
.meta{{color:#666;font-size:13px;margin:4px 0}}
.meta code{{background:#f0f0f0;padding:2px 6px;border-radius:3px;font-size:12px}}
.summary-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:20px 0}}
.card{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);text-align:center}}
.card .value{{font-size:28px;font-weight:700;color:#1a73e8}}
.card .label{{font-size:13px;color:#666;margin-top:4px}}
.card.warn .value{{color:#e8710a}}
.card.danger .value{{color:#d93025}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;
    overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06);margin:16px 0}}
th{{background:#1a73e8;color:#fff;padding:12px 16px;text-align:left;font-weight:600;cursor:pointer}}
th:hover{{background:#1557b0}}
td{{padding:10px 16px;border-bottom:1px solid #eee}}
tr:hover td{{background:#f0f7ff}}
td code{{background:#f0f0f0;padding:2px 8px;border-radius:4px;font-size:13px}}
.group{{background:#fff;border-radius:8px;margin:12px 0;box-shadow:0 2px 8px rgba(0,0,0,.06);overflow:hidden}}
.group-header{{padding:12px 16px;cursor:pointer;display:flex;justify-content:space-between;align-items:center}}
.group-header:hover{{background:#f0f7ff}}
.group-body{{padding:0 16px 16px;display:none}}
.group.open .group-body{{display:block}}
.group-header .arrow{{transition:transform .2s;margin-right:8px}}
.group.open .group-header .arrow{{transform:rotate(90deg)}}
.cross-app{{border-left:4px solid #e8710a}}
.cross-app .group-header{{background:#fff8f0}}
.tag{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;margin-left:8px}}
.tag-cross{{background:#fce4b8;color:#b36b00}}
.tag-size{{background:#e8f0fe;color:#1a73e8}}
.file-list{{list-style:none;padding:0;margin:8px 0}}
.file-list li{{padding:4px 0;font-family:monospace;font-size:13px;color:#555}}
.md5{{color:#999;font-size:12px;font-family:monospace}}
.filter-bar{{margin:12px 0;display:flex;gap:12px;align-items:center}}
.filter-bar input{{padding:8px 12px;border:1px solid #ddd;border-radius:6px;font-size:14px;width:300px}}
.filter-bar label{{font-size:13px;color:#666}}
</style>
</head><body>
{body}
<script>
document.querySelectorAll('.group').forEach(g=>{{
  g.querySelector('.group-header').addEventListener('click',()=>g.classList.toggle('open'))
}});
const fi=document.getElementById('groupFilter');
if(fi)fi.addEventListener('input',()=>{{
  const v=fi.value.toLowerCase();
  document.querySelectorAll('.group').forEach(g=>{{
    g.style.display=g.textContent.toLowerCase().includes(v)?'':'none'
  }})
}});
const cb=document.getElementById('crossOnly');
if(cb)cb.addEventListener('change',()=>{{
  document.querySelectorAll('.group').forEach(g=>{{
    if(cb.checked)g.style.display=g.classList.contains('cross-app')?'':'none';
    else g.style.display=''
  }})
}});
</script>
</body></html>"""


def generate_dup_report_html(
    duplicates: Dict[str, Tuple[List[str], int]],
    total_files: int,
    total_size: int,
    root_path: str,
    ignore_dirs: Set[str],
    extensions: Set[str],
    prefixes: Set[str],
    output_file: Optional[str] = None,
) -> str:
    """Generate duplicate files report in HTML format"""

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    parts: List[str] = []
    parts.append("<h1>Duplicate File Report</h1>")

    # Metadata
    parts.append(
        f'<p class="meta">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>'
    )
    parts.append(f'<p class="meta">Scanned: <code>{esc(root_path)}</code></p>')
    if ignore_dirs:
        parts.append(
            f'<p class="meta">Ignored: {", ".join(f"<code>{esc(d)}</code>" for d in sorted(ignore_dirs))}</p>'
        )
    if extensions:
        parts.append(f'<p class="meta">Extensions: {", ".join(sorted(extensions))}</p>')

    # Summary cards
    dup_count = sum(len(files) for files, _ in duplicates.values())
    dup_groups = len(duplicates)
    wasted = sum(size * (len(files) - 1) for files, size in duplicates.values())

    cards = [
        ("Total Files", f"{total_files:,}", ""),
        ("Total Size", format_size(total_size), ""),
        ("Duplicate Groups", f"{dup_groups:,}", "warn"),
        ("Duplicate Files", f"{dup_count:,}", "warn"),
        ("Wasted Space", format_size(wasted), "danger"),
    ]
    parts.append('<div class="summary-grid">')
    for label, value, cls in cards:
        parts.append(
            f'<div class="card {cls}"><div class="value">{value}</div><div class="label">{label}</div></div>'
        )
    parts.append("</div>")

    if not duplicates:
        parts.append("<h2>No duplicate files found!</h2>")
        html = _HTML_TEMPLATE.format(body="\n".join(parts))
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"\nReport saved to: {output_file}")
        return html

    sorted_dups = sorted(duplicates.items(), key=lambda x: x[1][1], reverse=True)

    # Directory stats table
    dir_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"count": 0, "size": 0})
    for _, (paths, size) in duplicates.items():
        for p in paths:
            d = os.path.dirname(p) or "."
            dir_stats[d]["count"] += 1
            dir_stats[d]["size"] += size

    parts.append("<h2>Duplicate Files by Directory</h2>")
    parts.append("<table><tr><th>Directory</th><th>Files</th><th>Size</th></tr>")
    for d, st in sorted(dir_stats.items(), key=lambda x: x[1]["size"], reverse=True):
        parts.append(
            f"<tr><td><code>{esc(d)}</code></td><td>{st['count']}</td><td>{format_size(st['size'])}</td></tr>"
        )
    parts.append("</table>")

    # Duplicate groups
    parts.append("<h2>Duplicate Details</h2>")
    parts.append('<div class="filter-bar">')
    parts.append('<input id="groupFilter" placeholder="Filter by path or filename...">')
    parts.append(
        '<label><input type="checkbox" id="crossOnly"> Cross-directory only</label>'
    )
    parts.append("</div>")

    for idx, (file_hash, (paths, size)) in enumerate(sorted_dups, 1):
        apps = sorted(set(p.split("/")[0] for p in paths))
        cross = len(apps) > 1
        cross_cls = "cross-app" if cross else ""
        cross_tag = '<span class="tag tag-cross">cross-dir</span>' if cross else ""
        apps_str = " &harr; ".join(esc(a) for a in apps)
        save = format_size(size * (len(paths) - 1))

        parts.append(f'<div class="group {cross_cls}">')
        parts.append('<div class="group-header">')
        parts.append(
            f'<span><span class="arrow">&#9654;</span>'
            f"Group {idx} &mdash; <strong>{len(paths)} files</strong>"
            f" &times; {format_size(size)} [{apps_str}]{cross_tag}</span>"
        )
        parts.append(f'<span class="tag tag-size">save {save}</span>')
        parts.append("</div>")
        parts.append('<div class="group-body"><ul class="file-list">')
        for p in sorted(paths):
            parts.append(f"<li>{esc(p)}</li>")
        parts.append(f'</ul><div class="md5">MD5: {file_hash}</div></div></div>')

    html = _HTML_TEMPLATE.format(body="\n".join(parts))
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\nReport saved to: {output_file}")
    return html


# ============ Unused Resources Functions ============

# Conservative matching: require filename stem to appear in a
# string-literal context (quoted, path-separated, or as a format
# pattern).  Short stems (<=3 chars) demand stricter evidence to
# avoid false positives from common variable/function names.

MIN_STEM_LENGTH_FOR_LOOSE_MATCH = 4


def scan_resource_files(
    resource_path: str, ignore_dirs: Set[str], extensions: Set[str]
) -> Dict[str, Tuple[str, int]]:
    """Scan resource files with specified extensions in resource directory"""
    resource_files: Dict[str, Tuple[str, int]] = {}
    root = Path(resource_path).resolve()
    ext_desc = ", ".join(sorted(extensions))

    print(f"Scanning resource directory: {root}")

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                filepath = os.path.join(dirpath, filename)
                try:
                    file_size = os.path.getsize(filepath)
                    rel_path = os.path.relpath(filepath, root)
                    resource_files[rel_path] = (filepath, file_size)
                except OSError as e:
                    print(
                        f"Warning: Cannot access file {filepath}: {e}", file=sys.stderr
                    )

    print(
        f"Found {len(resource_files)} resource files ({ext_desc}) in resource directory"
    )
    return resource_files


def _is_referenced_in_content(stem: str, content: str, resource_exts: Set[str]) -> bool:
    """Check if a resource file stem is referenced in code content.

    Uses conservative matching strategy with multiple confidence levels.
    Matching rules are ordered from high to low confidence, returns True
    on first hit.

    Args:
        stem: resource filename without extension (e.g. "reminder",
              "anim0", "findphone_23")
        content: full text content of a code file
        resource_exts: set of resource file extensions (e.g. {".bin"})
    """

    # Rule 1 [HIGH]: exact "stem.ext" substring
    # e.g. code has: lv_img_set_src(img, "/res/reminder.bin");
    for ext in resource_exts:
        if f"{stem}{ext}" in content:
            return True

    # Rule 2 [HIGH]: path separator before stem: "/stem"
    # e.g. code has: #define IMG OTA_PATH "/reminder"
    if f"/{stem}" in content:
        return True

    # Rule 3 [MEDIUM]: stem wrapped in quotes: "stem" or 'stem'
    # e.g. code has: dsc.name = "reminder";
    if f'"{stem}"' in content or f"'{stem}'" in content:
        return True

    # Rule 4-7: numbered file handling
    # For files like anim0.bin, Measuring45.bin, findphone_23.bin,
    # strip trailing digits to get base_stem (anim, Measuring,
    # findphone_), then try matching with base_stem
    base_stem = re.sub(r"\d+$", "", stem)
    if base_stem and base_stem != stem:
        # Rule 4 [MEDIUM]: path separator before base_stem: "/base_stem"
        # e.g. code has: prefix_name = MAKE_PATH("/measure/Measuring");
        if f"/{base_stem}" in content:
            return True

        # Rule 5 [MEDIUM]: base_stem wrapped in quotes
        # e.g. code has: dsc.prefix = "Measuring";
        if f'"{base_stem}"' in content or f"'{base_stem}'" in content:
            return True

        # Rule 6 [MEDIUM]: base_stem followed by format specifier
        # e.g. code has: snprintf(path, "%s/anim%d.bin", dir, idx);
        if re.search(rf'["\'/]{re.escape(base_stem)}%[dsx0-9]', content):
            return True

        # Rule 7 [MEDIUM]: base_stem as standalone word (len >= 4)
        # e.g. code has: APP_ANIM_PATH(findphone_)
        #      or:       #define PREFIX findphone_
        if len(base_stem) >= 4 and re.search(rf"\b{re.escape(base_stem)}\b", content):
            return True

    # Short stems (<=3 chars like "ab", "ok") are too common as
    # variable/function names, stop here to avoid false positives
    if len(stem) < MIN_STEM_LENGTH_FOR_LOOSE_MATCH:
        return False

    # Rule 8 [LOW]: stem followed by format specifier
    # e.g. code has: snprintf(path, "icon%s", suffix);
    if re.search(rf'"{re.escape(stem)}%[dsx0-9]', content):
        return True

    # Rule 9 [LOW]: stem inside any quoted string AND resource extension
    # exists in the same file. Catches split-suffix patterns like:
    # snprintf(path, "%s/fail.%s", dir, "bin");
    if re.search(rf'["\'][^"\']*{re.escape(stem)}[^"\']*["\']', content) and any(
        ext in content for ext in resource_exts
    ):
        return True

    return False


def find_unused_resources(
    bin_files: Dict[str, Tuple[str, int]],
    code_path: str,
    ignore_dirs: Set[str],
    file_extensions: Set[str],
    resource_exts: Set[str],
) -> Tuple[Dict[str, Tuple[str, int]], Dict[str, str]]:
    """Find unused resources using conservative filename-based matching.

    For each resource file, extract the stem (filename without extension)
    and search code files for references to that stem in string-literal
    contexts.
    """

    # Build stem -> [resource_paths] mapping
    stem_to_paths: Dict[str, List[str]] = defaultdict(list)
    # Pre-compute base stems (strip trailing digits) for numbered files
    stem_to_base: Dict[str, str] = {}
    for bin_path in bin_files:
        basename = os.path.basename(bin_path)
        raw_stem = os.path.splitext(basename)[0]
        stem = raw_stem.strip("_ \t")
        if not stem:
            stem = raw_stem
        stem_to_paths[stem].append(bin_path)
        base = re.sub(r"\d+$", "", stem)
        if base and base != stem:
            stem_to_base[stem] = base

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
                print(f"Scanned {file_count} code files...", end="\r", flush=True)

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except (IOError, OSError):
                continue

            # Fast pre-filter: only check stems that appear as
            # substring in this file (plain `in` is ~100x faster
            # than regex).  Also include stems whose base_stem
            # appears (for numbered files like anim0 -> anim).
            candidates = set()
            for stem in unmatched_stems:
                if stem in content:
                    candidates.add(stem)
                elif stem in stem_to_base:
                    base = stem_to_base[stem]
                    if base in content:
                        candidates.add(stem)

            if not candidates:
                continue

            newly_matched = []
            rel_code = os.path.relpath(filepath, root)
            for stem in candidates:
                if _is_referenced_in_content(stem, content, resource_exts):
                    for bin_path in stem_to_paths[stem]:
                        referenced_files.add(bin_path)
                    match_details[stem] = rel_code
                    newly_matched.append(stem)

            for stem in newly_matched:
                unmatched_stems.discard(stem)

    print(
        f"Scanned {file_count} code files, "
        f"matched {len(referenced_files)}/{len(bin_files)} resource files" + " " * 20
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
    extensions: Set[str],
    output_file: Optional[str] = None,
) -> str:
    """Generate unused resources report"""
    ext_desc = ", ".join(sorted(extensions))
    lines = []

    lines.append(f"# Unused Resource File Report ({ext_desc})")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Command**: `{' '.join(sys.argv)}`")
    lines.append(f"**Code Path**: `{code_path}`")
    lines.append(f"**Resource Path**: `{resource_path}`")
    lines.append(f"**Resource Extensions**: {ext_desc}")

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
    lines.append(f"Found **{unused_count}** unused resource files (sorted by size):")
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
    """Run unused resources detection mode"""
    if not os.path.isdir(args.code):
        print(f"Error: Code path does not exist: {args.code}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.dir):
        print(f"Error: Resource path does not exist: {args.dir}", file=sys.stderr)
        sys.exit(1)

    ignore_dirs = parse_ignore_dirs(args)
    extensions = parse_extensions(args)
    if not extensions:
        extensions = {".bin"}

    file_extensions: Set[str] = set(
        ext.strip() if ext.strip().startswith(".") else f".{ext.strip()}"
        for ext in args.code_ext.split(",")
    )

    ext_desc = ", ".join(sorted(extensions))
    print("=" * 60)
    print(f"Unused Resource File Detector ({ext_desc})")
    print("=" * 60)
    print()

    bin_files = scan_resource_files(args.dir, ignore_dirs, extensions)

    print()
    print("Analyzing unused resources...")
    unused_files, matched = find_unused_resources(
        bin_files, args.code, ignore_dirs, file_extensions, extensions
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
        os.path.abspath(args.dir),
        ignore_dirs,
        extensions,
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


def extract_base_name(filename: str) -> str:
    """Extract base name from filename, taking first part before first dot.

    Examples:
        confirm.indexed_8.png -> confirm
        confirm.png -> confirm
        icon.24.png -> icon
    """
    first_dot = filename.find(".")
    if first_dot == -1:
        return filename
    return filename[:first_dot]


def scan_files_for_diff(
    root_path: str,
    ignore_dirs: Set[str],
) -> Tuple[Dict[str, Tuple[str, int]], Dict[str, int]]:
    """Scan files and return mapping of key -> (full_path, size), and dir -> count.

    key = relative_dir/base_name (e.g., settings/icon/confirm)
    This handles same filenames in different directories.
    """
    files_by_key: Dict[str, Tuple[str, int]] = {}
    dir_stats: Dict[str, int] = defaultdict(int)
    root = Path(root_path).resolve()

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        for filename in filenames:
            if filename.startswith("."):
                continue
            base_name = extract_base_name(filename)
            if not base_name:
                continue
            filepath = os.path.join(dirpath, filename)
            try:
                file_size = os.path.getsize(filepath)
                rel_path = os.path.relpath(filepath, root)
                dir_path = os.path.dirname(rel_path)
                key = f"{dir_path}/{base_name}" if dir_path else base_name
                if dir_path not in dir_stats:
                    dir_stats[dir_path] = 0
                dir_stats[dir_path] += 1
                files_by_key[key] = (rel_path, file_size)
            except OSError as e:
                print(f"Warning: Cannot access file {filepath}: {e}", file=sys.stderr)

    return files_by_key, dict(dir_stats)


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


def generate_diff_report(
    files1: Dict[str, Tuple[str, int]],
    files2: Dict[str, Tuple[str, int]],
    only_in_path1: Set[str],
    only_in_path2: Set[str],
    common_keys: Set[str],
    dir_stats1: Dict[str, int],
    dir_stats2: Dict[str, int],
    path1: str,
    path2: str,
    ignore_dirs: Set[str],
    output_file: Optional[str] = None,
) -> str:
    """Generate diff mode report"""
    lines = []

    lines.append("# Directory Comparison Report (Diff Mode)")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Command**: `{' '.join(sys.argv)}`")
    lines.append(f"**Path1**: `{path1}`")
    lines.append(f"**Path2**: `{path2}`")

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
    lines.append(f"| Total files in Path1 | {len(files1):,} |")
    lines.append(f"| Total files in Path2 | {len(files2):,} |")
    lines.append(f"| Files only in Path1 | {len(only_in_path1):,} |")
    lines.append(f"| Files only in Path2 | {len(only_in_path2):,} |")
    lines.append(f"| Common files | {len(common_keys):,} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 📁 File Count by Directory")
    lines.append("")
    lines.append(f"### Path1: `{path1}`")
    lines.append("")
    lines.append("| Directory | File Count |")
    lines.append("|-----------|------------|")
    for dir_path, count in sorted(dir_stats1.items()):
        lines.append(f"| `{dir_path or '.'}` | {count} |")

    lines.append("")
    lines.append(f"### Path2: `{path2}`")
    lines.append("")
    lines.append("| Directory | File Count |")
    lines.append("|-----------|------------|")
    for dir_path, count in sorted(dir_stats2.items()):
        lines.append(f"| `{dir_path or '.'}` | {count} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    if only_in_path1:
        lines.append(f"## 📋 Files Only in Path1 ({len(only_in_path1)})")
        lines.append("")
        for idx, key in enumerate(sorted(only_in_path1), 1):
            path1_info = files1[key]
            lines.append(f"{idx}. `{path1_info[0]}`")
        lines.append("")
        lines.append("---")
        lines.append("")

    if only_in_path2:
        lines.append(f"## 📋 Files Only in Path2 ({len(only_in_path2)})")
        lines.append("")
        for idx, key in enumerate(sorted(only_in_path2), 1):
            path2_info = files2[key]
            lines.append(f"{idx}. `{path2_info[0]}`")
        lines.append("")
        lines.append("---")
        lines.append("")

    if not only_in_path1 and not only_in_path2:
        lines.append("✅ **All files match!**")
        lines.append("")
    else:
        lines.append("❌ **Differences found!**")
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
    lines.append(f"**Command**: `{' '.join(sys.argv)}`")
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

            lines.append(f"Found **{len(unused_files)}** unused resource files:")
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
Mode Description:
  dup     - Find duplicate files by content hash (default)
  unused  - Find resources not referenced in code (default: .bin)
  both    - Run both dup + unused checks in one command
  diff    - Compare two directories and find missing/extra files

Examples:

  1. Find duplicate files (dup mode, default):

    %(prog)s -d ./res -e bin
    %(prog)s -d ./res -e bin png
    %(prog)s -d ./res -e bin --action delete
    %(prog)s -d ./res -e bin -p theme_ config_

  2. Find duplicate files with directory ignore:

    %(prog)s -d ./res -e bin -i .git,node_modules
    %(prog)s -d ./applications -e bin png -i po,view_65,view_66,view_67

  3. Auto view variant detection (dup mode):

    When scanning a directory containing view/view_XX sub-directories
    with res* sub-directories (e.g., view/res_480_480, view_65/res),
    the tool automatically detects these variants and prompts a
    single-select menu. Default selection is the variant with the
    most files. This is skipped when -i is manually specified.

    %(prog)s -d ./applications -e bin png

  4. Find unused resources (unused mode):

    %(prog)s -m unused -c ./apps -d ./res
    %(prog)s -m unused -c ./apps -d ./res -e bin png
    %(prog)s -m unused -c ./apps -d ./res --prefix "/resource/app:"
    %(prog)s -m unused -c ./apps -d ./res --code-ext ".c,.h,.cpp,.java"

  5. Run both checks (both mode):

    %(prog)s -m both -d ./res -c ./apps -e bin

  6. Compare two directories (diff mode):

    %(prog)s -m diff --path1 ./design --path2 ./res
    %(prog)s -m diff --path1 ./design/app --path2 ./res/app
    %(prog)s -m diff --path1 ./design --path2 ./res --sort count
    %(prog)s -m diff --path1 ./design --path2 ./res -i .git,__pycache__

  7. Output control:

    Reports are generated in both Markdown and HTML formats.
    After generation, you will be prompted to open the HTML
    report in your browser.

    %(prog)s -d ./res -e bin -o my_report.md
    %(prog)s -d ./res -e bin --no-output
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
        help="Target directory to scan (duplicates scan dir or resource dir, "
        "default: current directory)",
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
        help="Code directory to scan for resource references (required for unused/both mode)",
    )
    parser.add_argument(
        "--code-ext",
        metavar="EXTS",
        default=".c,.h,.cpp,.hpp,.cc,.cxx,.py,.java,.js,.ts,.json",
        help="Code file extensions to scan for references "
        "(comma-separated, default: .c,.h,.cpp,.hpp,.cc,.cxx,"
        ".py,.java,.js,.ts,.json)",
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

    # Validate arguments based on mode
    if args.mode == "unused":
        if not args.code:
            print("Error: --code is required for unused mode", file=sys.stderr)
            sys.exit(1)

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
