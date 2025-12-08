#!/usr/bin/env python3
# -*- coding:UTF-8 -*-
#
# Copyright (C) 2023 Junbo Zheng. All rights reserved.
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

import shutil
import subprocess
import sys
import os
import gzip
import glob
import re
import logging as log

import argparse
from enum import IntEnum

try:
    from miwear import __version__
except ImportError:
    __version__ = "0.0.1"


log.basicConfig(
    level=log.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
    format="%(asctime)-19s.%(msecs)03d %(levelname)-8s %(filename)s %(lineno)-3d %(process)d %(message)s",
)


class DefaultCLIParameters:
    remote_path = "/sdcard/Android/data/com.mi.health/files/log/devicelog"
    source_path = "."
    output_path = "./file"
    output_file = "file.tar.gz"
    file_name = "log.tar.gz"
    filter_pattern = "log\\d*|tmp.log"
    tmp_log = "tmp.log"
    special_file_suffix = [".core", ".txt"]


class ShellRunner:
    @staticmethod
    def command_run(command):
        return subprocess.run(
            command, stdin=sys.stdin, stdout=sys.stdout, shell=True
        ).returncode


class CLIParametersParser:
    def __init__(self):
        # log.debug("Parameter Number :%d", len(sys.argv))
        # log.debug("Shell Name       :%s", str(sys.argv[0]))

        arg_parser = argparse.ArgumentParser(
            description="Extract a file with the suffix `.tar.gz` from the source path or remote path and extract to "
            "output_path."
        )

        arg_parser.add_argument(
            "--version",
            action="store_true",
            help="Show miwear_log version and exit.",
        )

        arg_parser.add_argument(
            "-o",
            "--output_path",
            type=str,
            nargs="+",
            default=DefaultCLIParameters.output_path,
            help="extract packet output path",
        )
        arg_parser.add_argument(
            "-s",
            "--source_path",
            type=str,
            nargs="+",
            default=DefaultCLIParameters.source_path,
            help="extract packet from source path",
        )
        arg_parser.add_argument(
            "-m",
            "--merge_file",
            type=str,
            nargs="?",
            help="extract packet and merge to a new file",
        )
        arg_parser.add_argument(
            "-f",
            "--filename",
            type=str,
            nargs=1,
            default=DefaultCLIParameters.file_name,
            help="extract packet filename, the default file suffix is .tar.gz, such as: log.tar.gz",
        )
        arg_parser.add_argument(
            "-p",
            "--purge_source_file",
            help="purge source file if is true",
            action="store_true",
            default=False,
        )
        arg_parser.add_argument(
            "-F",
            "--filter_pattern",
            type=str,
            default=DefaultCLIParameters.filter_pattern,
            help="filter the files to be merged",
        )
        arg_parser.add_argument(
            "-l",
            "--log",
            type=str,
            default=DefaultCLIParameters.tmp_log,
            help="special log file name(default: tmp.log)",
        )

        self.__cli_args = arg_parser.parse_args()
        if self.__cli_args.version:
            print("miwear_log version %s" % __version__)
            sys.exit(0)

        input_str = self.filename[0]

        if re.search(r"\d+", input_str):
            numbers = re.findall(r"\d+", input_str)
            if numbers:
                self.filename[0] = numbers[0]
                log.debug(
                    f"Extracted number '{self.filename[0]}' from input '{input_str}'"
                )
        else:
            pattern = r"^(.*?)\.tar.*\.gz$"
            match = re.match(pattern, input_str)
            if match:
                self.filename[0] = match.group(1)

        # With the input filename parameter as merge file if merge file is not specified
        if self.merge_file is None:
            self.merge_file = os.path.join(os.getcwd(), self.filename[0] + ".log")

        log.debug("output_path      :%s", self.output_path)
        log.debug("source_path      :%s", self.source_path)
        log.debug("filename         :%s", self.filename)
        log.debug("purge_source_file:%s", self.purge_source_file)
        log.debug("merge_file       :%s", self.merge_file)

    def __getattr__(self, item):
        return self.__cli_args.__getattribute__(item)

    def __setattr__(self, name, value):
        if name == "_CLIParametersParser__cli_args":
            super().__setattr__(name, value)
        else:
            setattr(self.__cli_args, name, value)


class LogTools:
    def __init__(self, cli_parser):
        self.__cli_parser = cli_parser
        self.log_packet_path = None
        self.log_dir_path = None

    def clear_output_dir(self, ask=True):
        if not os.path.exists(self.__cli_parser.output_path):
            return 0

        # if output path exists, clear
        if ask:
            input_str = input(
                "The %s already exists, will cover it? [Y/N]\n"
                % self.__cli_parser.output_path
            )
            if input_str != "Y":
                log.debug("quit and exit")
                return -1
        cmd = "rm -rf " + self.__cli_parser.output_path
        # fmt: off
        log.debug(
            Highlight.Convert("clear") + " exist file %s by command %s",
            self.__cli_parser.output_path,
            cmd
        )
        # fmt: on
        return ShellRunner.command_run(cmd)

    def pull_packet(self):
        if self.__cli_parser.source_path[0] == "phone":
            self.__cli_parser.source_path[0] = DefaultCLIParameters.remote_path
            adb_cmd = "adb pull " + self.__cli_parser.source_path[0] + " " + "./"
            log.debug(adb_cmd)
            ShellRunner.command_run(adb_cmd)

            file = (
                os.getcwd()
                + "/devicelog/**/"
                + "*"
                + self.__cli_parser.filename[0]
                + "*.tar*.gz"
            )
            result = glob.glob(file, recursive=True)
        else:
            pattern = (
                self.__cli_parser.source_path[0]
                + "/"
                + "*"
                + self.__cli_parser.filename[0]
                + "*.tar*.gz"
            )
            result = glob.glob(pattern)

        if len(result) == 0:
            log.error(
                Highlight.Convert(
                    "Not found file packet, please check source path", Highlight.RED
                ),
                stack_info=True,
            )
            return -1

        # fmt: off
        log.debug(
            Highlight.Convert("pull") + " %s from %s",
            result,
            self.__cli_parser.source_path[0]
        )
        # fmt: on
        if len(result) > 1:
            index = input("Please input the file index you want to extract:\n")
            file = result[int(index)]
        else:
            file = result[0]

        path = os.path.dirname(file)
        output = self.__cli_parser.filename[0] + "_" + DefaultCLIParameters.output_file
        output = os.path.join(path, output)

        if self.__cli_parser.purge_source_file:
            log.debug("rename to %s", output)
            os.rename(file, output)
        else:
            log.debug("copy to %s", output)
            shutil.copyfile(file, output)
        if output is None:
            log.error(
                Highlight.Convert("not found file packet", Highlight.RED),
                stack_info=True,
            )
            return -1

        self.log_packet_path = output

        log.debug("output file %s", self.log_packet_path)
        return 0

    def __find_logfiles_path__(self):
        for root, dirs, files in os.walk(self.__cli_parser.output_path):
            for file in files:
                if file == self.__cli_parser.log:
                    self.log_dir_path = os.path.abspath(root)
                    return 0
        return -1

    def __find_special_files(self):
        special_files = []
        for root, dirs, files in os.walk(self.log_dir_path):
            for file in files:
                # Check if the file ends with any suffix in special_file_suffix
                for suffix in DefaultCLIParameters.special_file_suffix:
                    if file.lower().endswith(suffix.lower()):
                        special_files.append(os.path.join(root, file))
        return special_files

    def __remove_all_suffix_gz_file__(self):
        for root, dirs, files in os.walk(self.log_dir_path):
            for file in files:
                if os.path.splitext(file)[-1] == ".gz":
                    os.remove(os.path.join(root, file))
        return 0

    def __gunzip_all__(self):
        if not os.path.exists(self.log_dir_path):
            log.error(
                Highlight.Convert(
                    f"Not found log directory {self.log_dir_path}", Highlight.RED
                ),
                stack_info=True,
            )
            return -1

        dirs = os.listdir(self.log_dir_path)
        for file in dirs:
            if ".gz" in file:
                try:
                    filename = file.replace(".gz", "")
                    gzip_file_path = os.path.join(self.log_dir_path, file)
                    output_file_path = os.path.join(self.log_dir_path, filename)

                    with gzip.open(gzip_file_path, "rb") as gzip_file:
                        with open(output_file_path, "wb+") as f:
                            f.write(gzip_file.read())

                except EOFError as e:
                    log.error(f"file {file} maybe error, code: {e}")
                    continue
                except Exception as e:
                    log.error(f"file {file} error: {e}")
                    continue
        log.debug(Highlight.Convert("gunzip") + " all done")
        return 0

    def extract_special_files(self):
        special_files = self.__find_special_files()
        if not special_files:
            log.debug("No special files found")
            return 0

        log.debug("Special files found:")
        for special_file in special_files:
            log.debug(f"  -> {special_file}")
            des_path = os.path.join(os.getcwd(), os.path.basename(special_file))
            log.debug(f"Copying {special_file} to {des_path}")
            shutil.copy(special_file, des_path)
        return 0

    def extract_packet(self):
        if not os.path.exists(self.__cli_parser.output_path):
            os.makedirs(self.__cli_parser.output_path)

        cmd = "gzip -d " + self.log_packet_path
        log.debug(Highlight.Convert("gzip") + " by command " + cmd)
        ShellRunner.command_run(cmd)

        tar_package = self.log_packet_path.replace(".gz", "")
        cmd = "tar -xvf " + tar_package + " -C " + self.__cli_parser.output_path
        log.debug(Highlight.Convert("tar") + " by command " + cmd)

        if ShellRunner.command_run(cmd) != 0:
            log.error(
                Highlight.Convert(f"Run command failed: {cmd}", Highlight.RED),
                stack_info=True,
            )
            return -1

        cmd = "chmod -R 755" + " " + self.__cli_parser.output_path
        if ShellRunner.command_run(cmd) != 0:
            log.error(
                Highlight.Convert(f"Run command failed: {cmd}", Highlight.RED),
                stack_info=True,
            )
            return -1

        # tar_package is tmp file, since it's has replaced from .tar.gz to .tar, let's remove it
        os.remove(tar_package)

        # find log files dir path
        if self.__find_logfiles_path__() != 0:
            return -1

        # gunzip all *.gz files under path
        if self.__gunzip_all__() != 0:
            return -1

        # remove unused .gz files
        return self.__remove_all_suffix_gz_file__()

    # merge all file to a new file
    def merge_logfiles(self):
        file_list = os.listdir(self.log_dir_path)
        file_list.sort(key=lambda name: (len(name), name))
        log.debug(Highlight.Convert("merge") + " file list %s", file_list)

        if os.path.exists(self.__cli_parser.merge_file):
            log.debug("merge file exist, will remove")
            os.remove(self.__cli_parser.merge_file)

        files_to_merge = []
        for file in file_list:
            if re.match(self.__cli_parser.filter_pattern, file) is None:
                continue
            files_to_merge.append(os.path.join(self.log_dir_path, file))

        if not files_to_merge:
            log.warning("No files match the pattern to merge")
            return False

        try:
            with open(self.__cli_parser.merge_file, "wb") as outfile:
                for file_path in files_to_merge:
                    log.debug(f"prepare merge file {file_path}")
                    try:
                        with open(file_path, "rb") as f:
                            outfile.write(f.read())
                    except Exception as e:
                        log.warning(f"Failed to read {file_path}: {e}")
                        continue

            log.debug(
                "Successfully merged %d files to %s",
                len(files_to_merge),
                self.__cli_parser.merge_file,
            )
            return True

        except Exception as e:
            log.error(f"Failed to merge files: {e}")
            return False


def CHECK_ERROR_EXIT(ret):
    if ret:
        log.error(Highlight.Convert("failure", Highlight.RED), stack_info=True)
        exit(ret)


class Highlight(IntEnum):
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    WHITE = 37

    @staticmethod
    def Convert(msg, color=BLUE):
        return "\033[;%dm%s\033[0m" % (color, msg)


def main():
    cli_args = CLIParametersParser()
    logtools = LogTools(cli_args)

    # clear exist output dir
    CHECK_ERROR_EXIT(logtools.clear_output_dir())

    # pull log packet from phone or local, depends on command line parameters
    CHECK_ERROR_EXIT(logtools.pull_packet())

    # extract log packet
    CHECK_ERROR_EXIT(logtools.extract_packet())

    # extract special file
    CHECK_ERROR_EXIT(logtools.extract_special_files())

    # merge the log files to one file, then remove output dir
    if logtools.merge_logfiles() is True:
        logtools.clear_output_dir(False)
    log.debug(Highlight.Convert("Successful", Highlight.GREEN))


if __name__ == "__main__":
    main()
