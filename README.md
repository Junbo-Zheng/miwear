# Python Miwear

A comprehensive Python Miwear toolkit to extract and process archive log files.

## Features

- Supports batch extraction of `.tar.gz` , `.zip` and `.gz` files.
- Command-line tools for log processing, validation, merging and unzipping.
- Serial command sender for interacting with serial devices (requires `pyserial`).
- Designed for automation and integration into your workflow.
- No external dependencies for log processing tools (pure Python standard libraries).
- `pyserial` required for serial communication functionality.

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

### 6. Serial Command Sender

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
