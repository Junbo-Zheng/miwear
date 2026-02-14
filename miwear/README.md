# Python Miwear Tools Extract `log` Files

`miwear_log` is a Python tool for extracting files with the `.tar.gz` suffix from either **local** or **remote** (Android phone via adb) paths to a specified output directory. It also supports extracting all `.gz` files at the same time.

**Additionally**, `miwear_log` can merge all extracted files into a single new file. By default, the merged file is named `self.filename.log`, but you can customize the name using the `--merge_file` or `-m` option.

## Installation

This project requires the `pyserial` library for serial communication functionality. Install it using pip:

```bash
pip(3) install pyserial
```

If you want to use the `serialtool.py` tool for serial device interaction, make sure to install this dependency first.

# File Layout
For example, consider a compressed package named `123456_abc.tar.gz` containing other compressed files and logs:

```shell
.
└── log
    └── file
        ├── 1.gz
        ├── 2.gz
        ├── 3.gz
        ├── 4.gz
        └── tmp.log
```

Inside the `.tar.gz` package, you may find multiple `.gz` files and a specific log file (e.g., `tmp.log`) to help locate the `.gz` files. You can freely modify the log file name as needed.

# Getting Started

Clone the repository to your local machine:

```shell
git clone https://github.com/Junbo-Zheng/miwear
```

## Set Alias for Quick Access

Add the following alias to your shell configuration file for easier usage:

- For zsh:
    ```shell
    echo "alias miwear_log='python3 $(pwd)/log.py'" >> ~/.zshrc
    source ~/.zshrc
    ```
- For bash:
    ```shell
    echo "alias miwear_log='python3 $(pwd)/log.py'" >> ~/.bashrc
    source ~/.bashrc
    ```

Some additional useful aliases are provided. Add them to your shell configuration file (`~/.zshrc` or `~/.bashrc`) for quick access:

```bash
# Unzip the current .zip file (single file only)
alias zz='python3 $(pwd)/unzip.py'

# Unzip all .gz files and merge them
alias gz='python3 $(pwd)/gz.py'

# Unzip all .tar.gz files
alias tz='python3 $(pwd)/targz.py'
```

After adding these aliases, restart your terminal or run `source ~/.zshrc` (or `source ~/.bashrc`) to activate them.
You can then use `zz`, `gz`, or `tz` directly in your terminal for fast extraction operations.

# Usage

To see all available options, run:

```shell
miwear_log --help
```

Example output:

```
usage: miwear_log [-h] [--version] [-o OUTPUT_PATH [OUTPUT_PATH ...]]
                  [-m [MERGE_FILE]] [-f [FILENAME]] [--phone] [-p]
                  [-F FILTER_PATTERN] [-l LOG]
                  [file_path]

Extract a file with the suffix `.tar.gz` from the source path or remote path
and extract to output_path.

positional arguments:
  file_path             extract packet file path (positional argument),
                        alternative to -f option

options:
  -h, --help            show this help message and exit
  --version             Show miwear_log version and exit.
  -o OUTPUT_PATH [OUTPUT_PATH ...], --output_path OUTPUT_PATH [OUTPUT_PATH ...]
                        extract packet output path
  -m [MERGE_FILE], --merge_file [MERGE_FILE]
                        extract packet and merge to a new file
  -f [FILENAME], --filename [FILENAME]
                        extract file path (with full path or just filename),
                        such as: /path/to/log.tar.gz or log.tar.gz
  --phone               pull file from Android phone via adb
  -p, --purge_source_file
                        purge source file if is true
  -F FILTER_PATTERN, --filter_pattern FILTER_PATTERN
                        filter the files to be merged
  -l LOG, --log LOG     special log file name(default: tmp.log)
```

## Supported Extraction Methods

You can extract files from both local and remote sources:

```shell
+------------------------+---------------------+
|        Android         |   -----------+      |
|         Phone          |              |      |
|  /sdcard/Android/data  |              |      |
+------------------------+             \|/     |
                                               |
                                               \|/    miwear_log
                                                +-------------------> local output path
                                               /|\                  (./file path by default)
+----------------------+               /|\     |
|       Local          |                |      |
|   /path/to/file      |                |      |
+----------------------+     -----------+      |
+----------------------+-----------------------+
```

- **Local File**: To extract a `.tar.gz` file from a local path, run:

    **Method 1: Using positional argument (recommended)**

    ```shell
    miwear_log /Users/junbozheng/test/123456_abc.tar.gz
    ```

    **Method 2: Using -f option**

    ```shell
    miwear_log -f /Users/junbozheng/test/123456_abc.tar.gz
    ```

    If you have already downloaded the file, you can quickly extract it using `miwear_log`.

    You can also use just the filename if the file is in the current directory:

    ```shell
    miwear_log 123456_abc.tar.gz
    ```

- **Android Phone**: To extract a `.tar.gz` file from your phone via adb, run:

    ```shell
    miwear_log --phone -f 123456_abc
    ```

    `miwear_log` will use the `adb pull` command to transfer files from your phone to your local machine and then extract them.
    Make sure your computer is connected to your phone via USB or other methods before running the command.

# License

[miwear](https://github.com/Junbo-Zheng/miwear) is licensed under the Apache License. See the [LICENSE](./LICENSE) file for details.
