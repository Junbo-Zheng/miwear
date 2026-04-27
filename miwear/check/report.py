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

"""Report generation for duplicate, unused, diff, and combined modes."""

import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from miwear.check.scanner import format_size


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


_UNUSED_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Unused Resource Report</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    max-width:1400px;margin:0 auto;padding:20px;background:#f8f9fa;color:#333}}
h1{{color:#e8710a;border-bottom:3px solid #e8710a;padding-bottom:10px}}
h2{{color:#333;margin-top:30px}}
.meta{{color:#666;font-size:13px;margin:4px 0}}
.meta code{{background:#f0f0f0;padding:2px 6px;border-radius:3px;font-size:12px}}
.summary-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:20px 0}}
.card{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);text-align:center}}
.card .value{{font-size:28px;font-weight:700;color:#1a73e8}}
.card .label{{font-size:13px;color:#666;margin-top:4px}}
.card.warn .value{{color:#e8710a}}
.card.danger .value{{color:#d93025}}
.card.ok .value{{color:#1e8e3e}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;
    overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06);margin:16px 0}}
th{{background:#e8710a;color:#fff;padding:12px 16px;text-align:left;font-weight:600;cursor:pointer}}
th:hover{{background:#c75f00}}
td{{padding:10px 16px;border-bottom:1px solid #eee}}
tr:hover td{{background:#fff8f0}}
td code{{background:#f0f0f0;padding:2px 8px;border-radius:4px;font-size:13px}}
.filter-bar{{margin:12px 0;display:flex;gap:12px;align-items:center}}
.filter-bar input{{padding:8px 12px;border:1px solid #ddd;border-radius:6px;font-size:14px;width:300px}}
.filter-bar select{{padding:8px 12px;border:1px solid #ddd;border-radius:6px;font-size:14px}}
.filter-bar label{{font-size:13px;color:#666}}
.result-count{{font-size:13px;color:#666;margin-left:12px}}
</style>
</head><body>
{body}
<script>
function applyFilters(){{
  const q=(document.getElementById('fileFilter').value||'').toLowerCase();
  const d=document.getElementById('dirFilter').value;
  const rows=document.querySelectorAll('#unusedTable tbody tr');
  let n=0;
  rows.forEach(r=>{{
    const path=r.cells[1].textContent.toLowerCase();
    const dir=r.getAttribute('data-dir');
    const show=(!q||path.includes(q))&&(!d||dir===d);
    r.style.display=show?'':'none';
    if(show)n++;
  }});
  document.getElementById('resultCount').textContent=n+' files shown';
}}
document.getElementById('fileFilter').addEventListener('input',applyFilters);
document.getElementById('dirFilter').addEventListener('change',applyFilters);
document.querySelectorAll('#unusedTable th').forEach((th,i)=>{{
  let asc=true;
  th.addEventListener('click',()=>{{
    const rows=Array.from(document.querySelectorAll('#unusedTable tbody tr'));
    rows.sort((a,b)=>{{
      let av=a.cells[i].getAttribute('data-sort')||a.cells[i].textContent;
      let bv=b.cells[i].getAttribute('data-sort')||b.cells[i].textContent;
      if(!isNaN(av)&&!isNaN(bv))return asc?av-bv:bv-av;
      return asc?av.localeCompare(bv):bv.localeCompare(av);
    }});
    asc=!asc;
    const tb=document.querySelector('#unusedTable tbody');
    rows.forEach(r=>tb.appendChild(r));
  }});
}});
</script>
</body></html>"""


def generate_unused_report_html(
    unused_files: Dict[str, Tuple[str, int]],
    total_files: int,
    total_size: int,
    code_path: str,
    resource_path: str,
    ignore_dirs: Set[str],
    extensions: Set[str],
    output_file: Optional[str] = None,
) -> str:
    """Generate unused resources report in interactive HTML format"""

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    ext_desc = ", ".join(sorted(extensions))
    parts: List[str] = []
    parts.append("<h1>Unused Resource Report</h1>")

    # Metadata
    parts.append(
        f'<p class="meta">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>'
    )
    parts.append(f'<p class="meta">Code: <code>{esc(code_path)}</code></p>')
    parts.append(f'<p class="meta">Resources: <code>{esc(resource_path)}</code></p>')
    parts.append(f'<p class="meta">Extensions: {esc(ext_desc)}</p>')
    if ignore_dirs:
        parts.append(
            f'<p class="meta">Ignored: '
            f'{", ".join(f"<code>{esc(d)}</code>" for d in sorted(ignore_dirs))}</p>'
        )

    # Summary cards
    unused_count = len(unused_files)
    unused_size = sum(size for _, size in unused_files.values())
    used_count = total_files - unused_count
    pct = (unused_count / total_files * 100) if total_files > 0 else 0

    cards = [
        ("Total Resources", f"{total_files:,}", ""),
        ("Total Size", format_size(total_size), ""),
        ("Referenced", f"{used_count:,}", "ok"),
        ("Unused", f"{unused_count:,}", "danger" if unused_count else "ok"),
        ("Unused Size", format_size(unused_size), "danger" if unused_size else "ok"),
        ("Unused %", f"{pct:.1f}%", "warn" if pct > 10 else ""),
    ]
    parts.append('<div class="summary-grid">')
    for label, value, cls in cards:
        parts.append(
            f'<div class="card {cls}">'
            f'<div class="value">{value}</div>'
            f'<div class="label">{label}</div></div>'
        )
    parts.append("</div>")

    if not unused_files:
        parts.append("<h2>All resource files are referenced in code!</h2>")
        html = _UNUSED_HTML_TEMPLATE.format(body="\n".join(parts))
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"\nHTML report saved to: {output_file}")
        return html

    # Directory stats table
    dir_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"count": 0, "size": 0})
    for path, (_, size) in unused_files.items():
        d = os.path.dirname(path) or "."
        dir_stats[d]["count"] += 1
        dir_stats[d]["size"] += size

    parts.append("<h2>Unused Files by Directory</h2>")
    parts.append("<table><tr><th>Directory</th><th>Files</th><th>Size</th></tr>")
    for d, st in sorted(dir_stats.items(), key=lambda x: x[1]["size"], reverse=True):
        parts.append(
            f"<tr><td><code>{esc(d)}</code></td>"
            f"<td>{st['count']}</td>"
            f"<td>{format_size(st['size'])}</td></tr>"
        )
    parts.append("</table>")

    # Filter bar
    sorted_unused = sorted(unused_files.items(), key=lambda x: x[1][1], reverse=True)
    all_dirs = sorted(dir_stats.keys())

    parts.append("<h2>Unused Files Detail</h2>")
    parts.append('<div class="filter-bar">')
    parts.append('<input id="fileFilter" placeholder="Filter by filename or path...">')
    parts.append('<select id="dirFilter"><option value="">All directories</option>')
    for d in all_dirs:
        parts.append(f'<option value="{esc(d)}">{esc(d)}</option>')
    parts.append("</select>")
    parts.append(
        f'<span id="resultCount" class="result-count">'
        f"{unused_count} files shown</span>"
    )
    parts.append("</div>")

    # File table
    parts.append('<table id="unusedTable">')
    parts.append("<thead><tr><th>#</th><th>File Path</th><th>Size</th></tr></thead>")
    parts.append("<tbody>")
    for idx, (path, (_, size)) in enumerate(sorted_unused, 1):
        d = os.path.dirname(path) or "."
        parts.append(
            f'<tr data-dir="{esc(d)}">'
            f'<td data-sort="{idx}">{idx}</td>'
            f"<td><code>{esc(path)}</code></td>"
            f'<td data-sort="{size}">{format_size(size)}</td></tr>'
        )
    parts.append("</tbody></table>")

    html = _UNUSED_HTML_TEMPLATE.format(body="\n".join(parts))
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\nHTML report saved to: {output_file}")
    return html


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
