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

"""Scanner utilities for file hashing, duplicate detection, unused resource
detection, view variant detection, and directory diff scanning."""

import hashlib
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# ============ Argument Parsing Helpers ============


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

    # Rule 1b [HIGH]: C macro token stringification: MACRO(stem.ext)
    # e.g. code has: ACTIVITIES_APP_ICON_PATH(calories_32px.bin)
    # The macro uses #str to stringify, so the filename appears
    # as a bare token (no quotes) inside parentheses.
    for ext in resource_exts:
        if f"({stem}{ext})" in content:
            return True

    # Rule 1c [HIGH]: bare stem inside parentheses (macro without ext)
    # e.g. code has: APP_ICON_PATH(reminder)
    if f"({stem})" in content:
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

    Note: ignore_dirs is only used for resource scanning, NOT for code
    scanning. Code files inside view directories must still be scanned
    for resource references.
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
        # Do NOT filter dirnames by ignore_dirs here -- code files
        # inside view directories must be scanned for references.

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


# ============ Diff Mode Functions ============


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
