# Python Miwear

A comprehensive Python Miwear toolkit to extract and process archive log files.

## Features

- Supports batch extraction of `.tar.gz` , `.zip` and `.gz` files.
- Command-line tools for log processing, validation, merging and unzipping.
- Resource check tool for finding duplicate files, unused resources, and directory comparison, with automatic view variant detection and combined Markdown + HTML reports.
- Log analyzer for parsing MiWear AppID and screen log entries into CSV or interactive HTML reports.
- Serial command sender for interacting with serial devices (requires `pyserial`).
- YMODEM file transfer over serial port (requires `pyserial`).
- Designed for automation and integration into your workflow.
- Requires Python >= 3.10.
- No external dependencies for log processing and resource check tools (pure Python standard libraries).
- `pyserial` required for serial communication and YMODEM functionality.

## Installation

Install the latest release from `PyPI`:

```bash
pip(3) install miwear
```

If you plan to use the serial command sender tool, also install `pyserial`:

```bash
pip(3) install pyserial
```

Alternatively, install from source:

```bash
git clone https://github.com/Junbo-Zheng/miwear
cd miwear
pip install .
```

## Command-Line Tools

After installation, you get several standalone CLI tools:

- `miwear_log` : Main utility for extracting archive files.
- `miwear_assert` : Extract assertion information from logs.
- `miwear_gz` : Unzip and merge `.gz` log files.
- `miwear_tz` : Specialized extraction for `.tar.gz`.
- `miwear_uz` : Versatile archive decompression utility.
- `miwear_serial` : Serial command sender for interacting with serial devices (requires `pyserial`).
- `miwear_ymodem` : YMODEM file transfer over serial port (requires `pyserial`).
- `miwear_check` : Resource check tool for finding duplicate files, unused resources, and directory comparison. Generates Markdown + interactive HTML reports.
- `miwear_loganalyzer` : Log analyzer for MiWear — parses AppID and screen log entries, exports CSV or interactive HTML reports.

## Usage Examples

### 1. Main Extraction Utility

**Method 1: Using positional argument (recommended)**

```bash
miwear_log ~/Downloads/log.tar.gz
```

**Method 2: Using -f option**

```bash
miwear_log -f ~/Downloads/log.tar.gz
```

**Pull from Android phone via adb:**

```bash
miwear_log --phone -f 123456_abc
```

### 2. Assertion Log Parser

```bash
miwear_assert -i mi.log -o assert_log.txt
```

### 3. GZ Log Merger

```bash
miwear_gz --path ./logs --log_file my.log --output_file merged.log
```

### 4. Targz Extraction

```bash
miwear_tz --path ./logs
```

### 5. Unzip Utility

```bash
miwear_uz --path ./logs
```

### 6. Resource Check Tool

**Find duplicate files (default mode):**

```bash
miwear_check -d ./res -e bin
```

Scan multiple extensions or filter by file-name prefix:

```bash
miwear_check -d ./res -e bin png
miwear_check -d ./res -e bin -p theme_ config_
```

**Find duplicate files and delete duplicates:**

```bash
miwear_check -d ./res -e bin --action delete
```

**Auto view variant detection (dup mode):**

When the scan directory contains `view/` and `view_XX/` sub-directories with `res*` sub-directories (e.g., `view/res_480_480`, `view_65/res`), an interactive single-select menu is shown to pick one variant. The default selection is the variant with the most files. Skipped when `-i` is specified manually.

```bash
miwear_check -d ./applications -e bin png
```

**Find unused resources:**

```bash
miwear_check -m unused -c ./apps -d ./res
```

**Find unused resources with path prefix mapping:**

```bash
miwear_check -m unused -c ./apps -d ./res --prefix "/resource/app:"
```

**Run both checks (duplicate + unused):**

```bash
miwear_check -m both -d ./res -c ./apps -e bin
```

**Compare two directories (diff mode):**

Compare files between two directories (e.g., design folder with PNG files vs converted folder with BIN files):

```bash
miwear_check -m diff --path1 ./design --path2 ./res
```

Compare specific subdirectories:

```bash
miwear_check -m diff --path1 ./design/app --path2 ./res/app
```

Ignore specific directories:

```bash
miwear_check -m diff --path1 ./design --path2 ./res -i .git,node_modules
```

Sort directory listing by file count instead of alphabetical:

```bash
miwear_check -m diff --path1 ./design --path2 ./res --sort count
```

**How diff mode works:**
- Compares files by extracting base name (first part before the first dot) from filenames
- Example: `confirm.indexed_8.png` and `confirm.bin` both have base name `confirm`, so they match
- Uses `relative_dir/base_name` as the comparison key, so same filenames in different subdirectories are handled correctly
- Reports files only in path1 (missing in path2), files only in path2 (extra), and common files
- Shows per-directory file count statistics for both paths

**Report output (Markdown + HTML):**

All modes generate a Markdown report and an accompanying interactive HTML report; you are prompted to open the HTML file in your browser when finished.

```bash
miwear_check -d ./res -e bin -o my_report.md
miwear_check -d ./res -e bin --no-output
miwear_check -m unused -c ./apps -d ./res --code-ext ".c,.h,.cpp,.java"
```

### 7. YMODEM File Transfer

Transfer a file via YMODEM over serial port:

```bash
miwear_ymodem -p /dev/ttyACM0 -b 921600 -f firmware.bin
```

### 8. Serial Command Sender

The `miwear_serial` tool requires the `pyserial` library. Install it with:

```bash
pip(3) install pyserial
```

#### Basic Usage

Open miniterm terminal (default behavior):

```bash
miwear_serial -p /dev/ttyACM0 -b 921600
```

Send a single command:

```bash
miwear_serial -p /dev/ttyUSB1 -b 115200 -c "ps"
```

Send a single command with response processing:

```bash
miwear_serial -p /dev/ttyUSB1 -b 115200 -c "ps" -r
```

#### Periodic Command Sending

Send command every 1 second:

```bash
miwear_serial -p /dev/ttyACM1 -i 1.0 -c "ps"
```

Send command 5 times with 2-second interval:

```bash
miwear_serial -p /dev/ttyACM1 -i 2.0 -c "ps" --count 5
```

#### Batch Command Execution

Send batch commands from file once:

```bash
miwear_serial -f commands.txt
```

Send batch commands every 2 seconds:

```bash
miwear_serial -f commands.txt -i 2.0
```

Send batch commands 5 times, every 2 seconds:

```bash
miwear_serial -f commands.txt -i 2.0 --count 5
```

#### Logging

Save all output to log file (default: miwear.log):

```bash
miwear_serial -p /dev/ttyACM0 -b 921600 -s
```

Save to specific log file:

```bash
miwear_serial -p /dev/ttyACM0 -b 921600 -s log.txt
```

#### Interactive Mode

For interactive command sending, use miniterm (default when no command specified):

```bash
miwear_serial -p /dev/ttyACM0 -b 921600
```

Press Ctrl+] to exit miniterm.

### 9. Log Analyzer

Parse MiWear log files (AppID entries and screen transitions) and export to CSV or an interactive HTML report.

Analyze all supported patterns (default) and write to `miwear.csv`:

```bash
miwear_loganalyzer -f 1.log
```

Export an interactive HTML report and open it in the browser:

```bash
miwear_loganalyzer -f 1.log --html --open-browser
```

Pick a specific analyzer (`appid`, `screen`, or `all`):

```bash
miwear_loganalyzer -f 1.log -t appid
miwear_loganalyzer -f 1.log -t screen -o screens.csv
```

**Each tool includes a `--help` option to display supported parameters and usage:**

```bash
miwear_log --help
miwear_assert --help
...
```

## License

Apache License 2.0

## Author and E-mail

- Junbo Zheng
- E-mail: 3273070@qq.com
