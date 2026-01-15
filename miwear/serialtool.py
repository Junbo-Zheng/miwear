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

import serial
import time
import threading
import argparse
import sys

from typing import Optional

try:
    from miwear import __version__
except ImportError:
    __version__ = "0.0.1"


class SerialCommander:
    """Serial command sender"""

    def __init__(
        self,
        port: str,
        baudrate: int,
        command: str = "ps",
        interval: float = 2.0,
        log_file: Optional[str] = None,
        count: int = -1,
        response: bool = False,
    ):
        self.port = port
        self.baudrate = baudrate
        self.periodic_interval = interval
        self.ser: Optional[serial.Serial] = None
        self.running = False
        self.send_thread: Optional[threading.Thread] = None
        self.command: str = command
        self.log_file = log_file
        self.log_enabled = log_file is not None
        self.count = count  # -1 means infinite, positive number means specific count
        self.current_count = 0  # Track current execution count
        self.response = response

    def _log(self, message: str):
        """log message to file if logging is enabled"""
        if self.log_enabled and self.log_file:
            try:
                timestamp = (
                    time.strftime("%Y-%m-%d %H:%M:%S")
                    + f".{int(time.time() * 1000) % 1000:03d}"
                )
                log_entry = f"[{timestamp}] {message}\n"
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry)
            except Exception as e:
                print(f"failed to write to log file: {e}")

    def connect(self) -> bool:
        """connect to serial port"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            msg = f"connected to {self.port} (Baudrate: {self.baudrate})"
            print(msg)
            self._log(msg)
            return True
        except serial.SerialException as e:
            msg = f"unable to connect to {self.port}: {e}"
            print(msg)
            self._log(msg)
            return False
        except Exception as e:
            msg = f"unexpected error: {e}"
            print(msg)
            self._log(msg)
            return False

    def disconnect(self):
        """Disconnect from serial port"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            msg = "serial connection disconnected"
            print(msg)
            self._log(msg)

    def send_command(self, command: str) -> bool:
        """Send a single command and receive response"""
        if not self.ser or not self.ser.is_open:
            msg = "serial port not connected"
            print(msg)
            self._log(msg)
            return False

        try:
            # Ensure command ends with carriage return and line feed
            if not command.endswith("\r\n"):
                command = command.rstrip("\r\n") + "\r\n"

            data = command.encode("ascii")

            # Clear receive buffer
            self.ser.reset_input_buffer()

            # Send command
            self.ser.write(data)
            # timestamp = (
            #     time.strftime("%Y-%m-%d %H:%M:%S")
            #     + f".{int(time.time() * 1000) % 1000:03d}"
            # )
            # print(f"[{timestamp}] Tx: {command.strip()}")
            tx_msg = f"{command.strip()}"

            timestamp = (
                time.strftime("%Y-%m-%d %H:%M:%S")
                + f".{int(time.time() * 1000) % 1000:03d}"
            )

            message = f"[{timestamp}] cmd: {tx_msg}, count -> {self.current_count}/{self.count}"
            print(message)
            self._log(message)

            # Wait for device processing and response
            time.sleep(0.3)

            # Read all available data
            response = b""
            start_time = time.time()
            max_wait_time = 3.0  # Maximum wait time: 3 seconds
            no_data_count = 0  # Continuous no-data counter

            while time.time() - start_time < max_wait_time:
                if self.ser.in_waiting > 0:
                    # Read all currently available data
                    chunk = self.ser.read(self.ser.in_waiting)
                    response += chunk
                    no_data_count = 0  # Reset counter
                    # Briefly wait to see if more data arrives
                    time.sleep(0.1)
                else:
                    # If no new data, increment counter
                    no_data_count += 1
                    time.sleep(0.05)

                    # Exit if no data for 5 consecutive checks (~0.25 seconds)
                    if no_data_count >= 5:
                        break

            # Display received data only if response is enabled
            if response and self.response:
                try:
                    response_text = response.decode("ascii", errors="replace").strip()
                    if response_text:
                        # timestamp = (
                        #     time.strftime("%Y-%m-%d %H:%M:%S")
                        #     + f".{int(time.time() * 1000) % 1000:03d}"
                        # )
                        # print(
                        #     f"[{timestamp}] Rx({len(response_text)} bytes): {response_text}",
                        #     end=" ",
                        # )
                        rx_msg = f"{response_text}"
                        print(rx_msg)
                        self._log(f"Rx({len(response_text)} bytes): {rx_msg}")
                    else:
                        msg = "empty response"
                        print(msg)
                        self._log(msg)
                except Exception as e:
                    rx_msg = f"{response!r} {e}"
                    print(rx_msg)
                    self._log(f"Rx(raw): {rx_msg}")
            elif response:
                # Just log the raw response without processing/displaying
                self._log(f"Rx({len(response)} bytes): raw_data_not_processed")
            else:
                msg = "no response"
                # print(msg)
                self._log(msg)

            return True
        except Exception as e:
            msg = f"failed to send command: {e}"
            print(msg)
            self._log(msg)
            return False

    def start_periodic_send(self, command: str, interval: float, count: int = -1):
        """Start periodic command sending"""
        if self.send_thread and self.send_thread.is_alive():
            msg = "✗ Periodic sending already running"
            print(msg)
            self._log(msg)
            return

        self.command = command.rstrip("\r\n")
        self.periodic_interval = interval
        self.count = count
        self.current_count = 0
        self.running = True

        self.send_thread = threading.Thread(target=self._periodic_worker, daemon=True)
        self.send_thread.start()

        count_msg = f"(count: {count})" if count != -1 else "(infinite)"
        msg = f"started periodic sending '{self.command}' (interval: {interval}s) {count_msg}"
        print(msg)
        self._log(msg)
        msg2 = "  Press Ctrl+C to stop"
        print(msg2)
        self._log(msg2)

    def stop_periodic_send(self):
        """Stop periodic sending"""
        self.running = False
        if self.send_thread:
            self.send_thread.join(timeout=2.0)
        msg = "periodic sending stopped"
        print(msg)
        self._log(msg)

    def _periodic_worker(self):
        """Periodic sending worker thread"""
        while self.running:
            try:
                self.send_command(self.command)
                self.current_count += 1

                # Check if we've reached the count limit
                if self.count != -1 and self.current_count >= self.count:
                    msg = (
                        f"Reached count limit ({self.count}), stopping periodic sending"
                    )
                    print(msg)
                    self._log(msg)
                    self.running = False
                    break

                time.sleep(self.periodic_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                msg = f"periodic sending error: {e}"
                print(msg)
                self._log(msg)
                time.sleep(1)

    def interactive_mode(self):
        """Interactive command mode"""
        intro = "\n=== Interactive Mode ==="
        print(intro)
        self._log(intro)
        install_hint = (
            "Note: This tool requires pyserial. Install with: pip(3) install pyserial"
        )
        print(install_hint)
        self._log(install_hint)
        help1 = "Enter commands to send to serial port, type 'exit' or 'quit' to exit"
        print(help1)
        self._log(help1)
        help2 = "Type 'periodic <command> <interval> [count]' to start periodic sending"
        print(help2)
        self._log(help2)
        help3 = "Type 'stop' to stop periodic sending"
        print(help3)
        self._log(help3)
        help4 = "Type 'help' to show help"
        print(help4)
        self._log(help4)
        sep = "=" * 30
        print(sep)
        self._log(sep)

        while True:
            try:
                cmd = input("Command> ").strip()
                self._log(f"user input: {cmd}")

                if not cmd:
                    continue

                if cmd.lower() in ["exit", "quit"]:
                    break
                elif cmd.lower() == "help":
                    self._show_interactive_help()
                elif cmd.lower() == "stop":
                    self.stop_periodic_send()
                elif cmd.lower().startswith("periodic "):
                    parts = cmd.split()
                    if len(parts) >= 2:
                        periodic_cmd = parts[1]
                        interval = float(parts[2]) if len(parts) >= 3 else 1.0
                        count = int(parts[3]) if len(parts) >= 4 else -1
                        self.start_periodic_send(periodic_cmd, interval, count)
                    else:
                        msg = "Usage: periodic <command> [interval_seconds] [count]"
                        print(msg)
                        self._log(msg)
                elif cmd.lower().startswith("send "):
                    # Send single command
                    single_cmd = cmd[5:].strip()
                    self.send_command(single_cmd)
                else:
                    # Default: send single command
                    self.send_command(cmd)

            except KeyboardInterrupt:
                msg = "\nReceived interrupt signal"
                print(msg)
                self._log(msg)
                break
            except EOFError:
                msg = "\nInput ended"
                print(msg)
                self._log(msg)
                break
            except Exception as e:
                msg = f"error: {e}"
                print(msg)
                self._log(msg)

    def _show_interactive_help(self):
        """Show interactive mode help"""
        help_text = [
            "\nInteractive mode commands:",
            "  help                    - Show this help",
            "  exit/quit               - Exit interactive mode",
            "  stop                    - Stop periodic sending",
            "  periodic <cmd> [int] [count] - Start periodic command sending",
            "  send <cmd>              - Send single command",
            "  <cmd>                   - Send single command (default)",
            "",
            "  Note: count defaults to -1 (infinite). Use positive number for specific count.",
            "",
            "Installation:",
            "  This tool requires pyserial. Install with: pip(3) install pyserial",
            "",
        ]
        for line in help_text:
            print(line)
            self._log(line)

    def send_batch_commands(
        self, commands_file: str, interval: float = 2.0, count: int = -1
    ):
        """Send batch commands from file with optional interval and count"""

        try:
            with open(commands_file, "r", encoding="utf-8") as f:
                commands = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]

            if not commands:
                msg = f"no valid commands found in {commands_file}"
                print(msg)
                self._log(msg)
                return

            msg = f"read {len(commands)} commands from {commands_file}"
            print(msg)
            self._log(msg)

            count_msg = f"(count: {count})" if count != -1 else "(infinite)"
            msg = (
                f"starting batch command execution (interval: {interval}s) {count_msg}"
            )
            print(msg)
            self._log(msg)
            msg2 = "  Press Ctrl+C to stop"
            print(msg2)
            self._log(msg2)

            self.current_count = 0
            while self.running and (count == -1 or self.current_count < count):
                for i, cmd in enumerate(commands, 1):
                    if not self.running:
                        break

                    batch_msg = f"[{i}/{len(commands)}] sending: {cmd}"
                    print(batch_msg)
                    self._log(batch_msg)
                    self.send_command(cmd)
                    time.sleep(0.2)  # Interval between commands within batch

                self.current_count += 1

                # Check if we've reached the count limit
                if count != -1 and self.current_count >= count:
                    msg = f"Reached count limit ({count}), stopping batch execution"
                    print(msg)
                    self._log(msg)
                    break

                # Sleep between batch runs if not the last run
                if self.running and (count == -1 or self.current_count < count):
                    time.sleep(interval)

        except FileNotFoundError:
            msg = f"command file not found: {commands_file}"
            print(msg)
            self._log(msg)
        except Exception as e:
            msg = f"failed to read command file: {e}"
            print(msg)
            self._log(msg)


def validate_baudrate(baudrate_str: str) -> int:
    """Validate and convert baudrate"""
    try:
        baudrate = int(baudrate_str)
        valid_rates = [
            9600,
            19200,
            38400,
            57600,
            115200,
            230400,
            460800,
            921600,
            1000000,
            2000000,
        ]
        if baudrate not in valid_rates:
            print(
                f"warning: Baudrate {baudrate} is not a common value, but will try to use"
            )
        return baudrate
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid baudrate: {baudrate_str}")


def start_miniterm(port: str, baudrate: int) -> bool:
    """Start serial.tools.miniterm for direct terminal access"""
    try:
        # Try to import serial.tools.miniterm
        from serial.tools import miniterm

        print(f"starting miniterm on {port} at {baudrate} baud")
        print("  Use Ctrl+] to exit miniterm")
        print("=" * 50)

        # Save original sys.argv and set up miniterm arguments
        original_argv = sys.argv
        sys.argv = ["miniterm", "--raw", "--eol", "LF", port, str(baudrate)]

        try:
            # Run miniterm with the correct arguments
            miniterm.main(default_port=port, default_baudrate=baudrate)
            return True
        finally:
            # Restore original sys.argv
            sys.argv = original_argv

    except ImportError:
        print("serial.tools.miniterm not available")
        print("Please install pyserial with: pip(3) install pyserial")
        return False
    except Exception as e:
        print(f"failed to start miniterm: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Serial command sender tool - for interacting with serial devices and sending commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Installation:
  This tool requires the pyserial library. Install it with:
  pip(3) install pyserial

Examples:
  %(prog)s -p /dev/ttyACM0 -b 921600                 # Open miniterm terminal (default behavior)
  %(prog)s -p /dev/ttyACM0 -b 921600 -c ""           # Open miniterm terminal (explicit)
  %(prog)s -p /dev/ttyUSB1 -b 115200 -c "ps"         # Send single command
  %(prog)s -p /dev/ttyUSB1 -b 115200 -c "ps" -r      # Send single command with response processing
  %(prog)s -p /dev/ttyACM1 -i 1.0 -c "ps"            # Send command periodically
  %(prog)s -p /dev/ttyACM1 -i 1.0 -c "ps" --count 5  # Send command 5 times
  %(prog)s -f commands.txt                           # Send batch commands once
  %(prog)s -f commands.txt -i 2.0                    # Send batch commands every 2 seconds
  %(prog)s -f commands.txt -i 2.0 --count 5          # Send batch commands 5 times, every 2 seconds
  %(prog)s -s                                        # Save all output to miwear.log
  %(prog)s -s log.txt                                # Save all output to log.txt
  %(prog)s --version                                 # Show version information
        """,
    )

    parser.add_argument(
        "--version", action="store_true", help="Show version information and exit"
    )

    parser.add_argument(
        "-p",
        "--port",
        type=str,
        default="/dev/ttyACM1",
        help="Specify serial device path (default: /dev/ttyACM1)",
    )

    parser.add_argument(
        "-b",
        "--baudrate",
        type=validate_baudrate,
        default=921600,
        help="Specify baudrate (default: 921600)",
    )

    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=2.0,
        help="Interval for periodic sending (seconds), used with -c",
    )

    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="Path to file containing command list, one per line. Can be used with -i and --count "
        "for repeated execution",
    )

    parser.add_argument(
        "-c",
        "--command",
        type=str,
        nargs="?",
        const="",  # If -c is specified without value, it becomes empty string
        default=None,  # If -c is not specified at all, it's None
        help="Single command to send. If not specified or empty, opens miniterm terminal",
    )

    parser.add_argument(
        "-s",
        "--save",
        nargs="?",
        const="miwear.log",
        type=str,
        help="Save all input/output to file (default: miwear.log)",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=-1,
        help="Number of periodic executions (-1 for infinite, default: -1)",
    )

    parser.add_argument(
        "-r",
        "--response",
        action="store_true",
        help="Process and display received data (default: disabled to avoid terminal interference)",
    )

    args = parser.parse_args()

    # Show version information
    if args.version:
        print(f"Serial Command Sender v{__version__}")
        sys.exit(0)

    # Handle log file setup
    log_file = None
    if args.save:
        log_file = args.save
        # Create or clear the log file
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("=== Serial Command Sender Log ===\n")
                f.write(f"Version   : {__version__}\n")
                f.write(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Port      : {args.port}\n")
                f.write(f"Baudrate  : {args.baudrate}\n")
                f.write(f"Interval  : {args.interval}\n")
                f.write(f"Count     : {args.count}\n")
                f.write("=" * 50 + "\n\n")
            print(f"logging enabled. All output will be saved to: {log_file}")
        except Exception as e:
            print(f"failed to create log file: {e}")
            log_file = None

    # Check if we should use miniterm (command is None or empty string, but no file specified)
    if (args.command is None or args.command == "") and not args.file:
        # Use miniterm for direct terminal access
        if not start_miniterm(args.port, args.baudrate):
            sys.exit(1)
        return

    # Create commander instance
    commander = SerialCommander(
        args.port,
        args.baudrate,
        args.command,
        args.interval,
        log_file,
        args.count,
        args.response,
    )

    # Connect to serial port
    if not commander.connect():
        sys.exit(1)

    try:
        # Mode selection
        if args.file:
            # Batch command mode with interval and count support
            commander.running = True
            commander.send_batch_commands(args.file, args.interval, args.count)
        elif args.command and args.interval:
            # Periodic sending mode
            commander.start_periodic_send(args.command, args.interval, args.count)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                commander.stop_periodic_send()
        else:
            # Single command mode
            commander.send_command(args.command)

    except KeyboardInterrupt:
        msg = "\nReceived interrupt signal, exiting..."
        print(msg)
        if log_file:
            commander._log(msg)
    finally:
        commander.stop_periodic_send()
        commander.disconnect()

        # Add summary to log file if logging is enabled
        if log_file:
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write("\n=== Session Ended ===\n")
                    f.write(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n")
            except Exception as e:
                print(f"failed to write session end to log file: {e}")


if __name__ == "__main__":
    main()
