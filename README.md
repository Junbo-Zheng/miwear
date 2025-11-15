# Python Miwear

A comprehensive Python Miwear toolkit to extract and process archive log files.

## Features

- Supports batch extraction of `.tar.gz` , `.zip` and `.gz` files.
- Command-line tools for log processing, validation, merging and unzipping.
- Designed for automation and integration into your workflow.
- No external dependencies, pure Python standard libraries.

## Installation

Install the latest release from `PyPI`:

```bash
pip(3) install miwear
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

## Usage Examples

### 1. Main Extraction Utility

```bash
miwear_log -s ~/Downloads -f log.tar.gz
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
