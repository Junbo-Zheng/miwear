<div align="center">

# miwear

A Python toolkit for extracting, merging, auditing and analyzing MiWear device dumps — from the command line.

[![PyPI version](https://img.shields.io/pypi/v/miwear.svg)](https://pypi.org/project/miwear/)
[![Python](https://img.shields.io/pypi/pyversions/miwear.svg)](https://pypi.org/project/miwear/)
[![License](https://img.shields.io/pypi/l/miwear.svg)](./LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/miwear.svg)](https://pypi.org/project/miwear/)

</div>

`miwear` bundles eight small, focused command-line tools for the everyday chores of working with MiWear (Xiaomi wearable) device artifacts — unpacking `.tar.gz` / `.zip` / `.gz` bundles, merging rotated logs, extracting assertions, auditing resource directories, parsing runtime log patterns, and driving serial consoles.

Each tool does one thing, takes sensible defaults, and produces human- or machine-readable output (plain text, CSV, Markdown, or interactive HTML).

## Highlights

- **Zero runtime dependencies** for the core tools — pure Python standard library
- **Batch extraction** for `.tar.gz`, `.zip` and `.gz` archives in a single pass
- **Log workflow**: pull logs via `adb`, merge rotated shards, extract assertions, filter by pattern
- **Resource audit**: duplicate detection, unused-asset scan, two-directory diff — with Markdown + interactive HTML reports
- **Log analyzer** for AppID / screen-transition patterns, exportable to CSV or interactive HTML
- **Optional serial console** (miniterm, one-shot, periodic, or batch-file modes) via `pyserial`
- Works on **Python 3.10+**, Linux / macOS / Windows

## Installation

```bash
# Core tools
pip install miwear

# Core + serial console helper
pip install 'miwear[serial]'
```

> [!TIP]
> Every command accepts `--help` for the full option list and `--version` to print the installed version.

## Quick start

```bash
# Extract and merge a device log bundle downloaded from the phone
miwear_log ~/Downloads/log.tar.gz

# Or pull straight from a connected Android device via adb
miwear_log --phone -f 123456_abc

# Audit a resources directory for duplicates and open an HTML report
miwear_check -d ./resources -e bin
```

## Commands

| Command              | Purpose                                                                       | Docs                                   |
| -------------------- | ----------------------------------------------------------------------------- | -------------------------------------- |
| `miwear_log`         | Extract a MiWear log archive and merge its contents into a single log file    | [↓](#miwear_log)                       |
| `miwear_assert`      | Extract assertion information from a log                                      | [↓](#miwear_assert)                    |
| `miwear_gz`          | Decompress and merge `.gz` log shards                                         | [↓](#miwear_gz)                        |
| `miwear_tz`          | Batch-extract `.tar.gz` archives in a directory                               | [↓](#miwear_tz--miwear_uz)             |
| `miwear_uz`          | Batch-extract `.zip` archives in a directory                                  | [↓](#miwear_tz--miwear_uz)             |
| `miwear_check`       | Resource audit — duplicates, unused assets, directory diff                    | [↓](#miwear_check)                     |
| `miwear_loganalyzer` | Parse AppID / screen log patterns into CSV or interactive HTML                | [↓](#miwear_loganalyzer)               |
| `miwear_serial`      | Serial console helper (requires `pyserial`)                                   | [↓](#miwear_serial)                    |

## Usage

### `miwear_log`

Extract a log bundle and merge its shards into one file.

```bash
# Positional path (recommended)
miwear_log ~/Downloads/log.tar.gz

# Explicit -f flag
miwear_log -f ~/Downloads/log.tar.gz

# Pull straight from an Android phone via adb
miwear_log --phone -f 123456_abc
```

### `miwear_assert`

Extract assertion blocks from a merged log.

```bash
miwear_assert -i mi.log -o assert_log.txt
```

### `miwear_gz`

Decompress and concatenate all `.gz` shards in a directory.

```bash
miwear_gz --path ./logs --log_file my.log --output_file merged.log
```

### `miwear_tz` / `miwear_uz`

Batch extract every archive in a directory.

```bash
miwear_tz --path ./logs     # *.tar.gz
miwear_uz --path ./logs     # *.zip
```

### `miwear_check`

Three audit modes: **duplicates** (default), **unused** assets, and **diff** between two directories. All modes emit a Markdown + interactive HTML report with search / filter / sort.

<details>
<summary><b>Duplicate detection</b></summary>

```bash
miwear_check -d ./resources -e bin
miwear_check -d ./resources -e bin png
miwear_check -d ./resources -e bin -p theme_ config_
miwear_check -d ./resources -e bin --action delete
```
</details>

<details>
<summary><b>Unused resource scan</b></summary>

`-d` sets where resources live; `-c` sets where to look for references (defaults to `-d`).

```bash
miwear_check -m unused -d ./project -e bin
miwear_check -m unused -d ./project -c ./project/ota -e bin
miwear_check -m unused -d ./project -e bin --code-ext ".c,.h,.cpp,.java"

# Run duplicate + unused together
miwear_check -m both -d ./project -e bin
```
</details>

<details>
<summary><b>Two-directory diff</b></summary>

Matches files by base name (everything before the first dot) under the same relative path — so `confirm.indexed_8.png` and `confirm.bin` pair up automatically.

```bash
miwear_check -m diff --path1 ./design --path2 ./converted
miwear_check -m diff --path1 ./design --path2 ./converted -i .git,node_modules
miwear_check -m diff --path1 ./design --path2 ./converted --sort count
```
</details>

<details>
<summary><b>Report output</b></summary>

```bash
miwear_check -d ./resources -e bin -o my_report.md
miwear_check -d ./resources -e bin --no-output
```
</details>

> [!NOTE]
> When the scan directory contains both `view/` and `view_XX/res*` variants, `miwear_check` prompts you to pick one (default: the variant with the most files). Pass `-i` to skip the prompt.

### `miwear_loganalyzer`

Parse MiWear runtime log patterns and export CSV or HTML.

```bash
# Default: all analyzers → miwear.csv
miwear_loganalyzer -f 1.log

# Interactive HTML report (opens in browser)
miwear_loganalyzer -f 1.log --html --open-browser

# Run a single analyzer
miwear_loganalyzer -f 1.log -t appid
miwear_loganalyzer -f 1.log -t screen -o screens.csv
```

### `miwear_serial`

> [!IMPORTANT]
> Requires `pyserial`. Install with `pip install 'miwear[serial]'`.

<details>
<summary><b>Interactive session</b></summary>

```bash
miwear_serial -p /dev/ttyACM0 -b 921600
# Press Ctrl+] to exit
```
</details>

<details>
<summary><b>One-shot command</b></summary>

```bash
miwear_serial -p /dev/ttyUSB1 -b 115200 -c "ps"
miwear_serial -p /dev/ttyUSB1 -b 115200 -c "ps" -r   # parse response
```
</details>

<details>
<summary><b>Periodic / batch</b></summary>

```bash
# Repeat on a timer
miwear_serial -p /dev/ttyACM1 -i 1.0 -c "ps"
miwear_serial -p /dev/ttyACM1 -i 2.0 -c "ps" --count 5

# Batch commands from a file
miwear_serial -f commands.txt
miwear_serial -f commands.txt -i 2.0 --count 5
```
</details>

<details>
<summary><b>Record to a log file</b></summary>

```bash
miwear_serial -p /dev/ttyACM0 -b 921600 -s              # miwear.log (default)
miwear_serial -p /dev/ttyACM0 -b 921600 -s log.txt      # custom path
```
</details>

## Requirements

- Python **3.10+**
- `pyserial` (only for `miwear_serial`)
