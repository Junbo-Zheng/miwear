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

import argparse
import re
import webbrowser
import os

from typing import Dict, List, Optional

# AppID to app name mapping (converted from C enum)
# Format: "APP_NAME": 0xXXXX
APP_NAME_TO_ID: Dict[str, int] = {
    "NONE": 0x0000,
    "LAUNCHER": 0x0001,
    "WATCHFACE": 0x0002,
    "PRESSURE": 0x0003,
    "BREATH": 0x0004,
    "HEARTRATE": 0x0005,
    "ACTIVITY": 0x0006,
    "ACTIVITY_RECORD": 0x0007,
    "ACTIVITY_RECORD_BACKUP": 0x0008,
    "CLOCK": 0x0009,
    "CLOCK_STOPWATCH": 0x000A,
    "CLOCK_TIMER": 0x000B,
    "SLEEP": 0x000C,
    "ENERGY": 0x000D,
    "OXYGEN": 0x000E,
    "SPORTS": 0x000F,
    "HOME": 0x0010,
    "SETUPWIZARD": 0x0011,
    "EXAMPLE": 0x0012,
    "ACTIVITIES": 0x0013,
    "NOTIFICATIONS": 0x0014,
    "MEDIA": 0x0015,
    "SETTINGS": 0x0016,
    "DEMO": 0x0017,
    "COMPASS": 0x0018,
    "OTA": 0x0019,
    "FLASHLIGHT": 0x001A,
    "CALENDAR": 0x001B,
    "REMOTE_CAMERA": 0x001C,
    "SPORTS_RECORD": 0x001D,
    "ALIPAY": 0x001E,
    "WOMENHEALTH": 0x001F,
    "CHRONOGRAPH": 0x0020,
    "WEATHER": 0x0021,
    "SYSTEM": 0x0022,
    "PHONE": 0x0023,
    "REMINDER": 0x0024,
    "WXPAY": 0x0025,
    "TIMER": 0x0026,
    "FIND_PHONE": 0x0027,
    "ALARM": 0x0028,
    "RECORDER": 0x0029,
    "BAROMETER": 0x002A,
    "NFCCARD": 0x002B,
    "DEBUG": 0x002C,
    "VOICE_ASSISTANT": 0x002D,
    "CONTACT": 0x002E,
    "SPORTS_COURSE": 0x002F,
    "TEMPERATURE": 0x0030,
    "SHARE": 0x0031,
    "DEMONSTRATE": 0x0032,
    "EASTER_EGG": 0x0033,
    "BLOOD_PRESSURE": 0x0034,
    "ECG": 0x0035,
    "VITALITY_VALUE": 0x0036,
    "JS": 0x0037,
    "LUA": 0x0038,
    "TRAINING_STATUS": 0x0039,
    "TOMATO_TIMER": 0x003A,
    "WORLD_CLOCK": 0x003B,
    "TODO_LIST": 0x003C,
    "PHONE_MUTE": 0x003D,
    "FALL": 0x003E,
    "MIJIA": 0x003F,
    "LPA": 0x0040,
    "CHECK_TOOL": 0x0041,
    "BLOOD_SUGAR": 0x0042,
    "INTERCONNECT": 0x0043,
    "SPORTS_TRAINING": 0x0044,
    "PERPETUAL_CALENDAR": 0x0045,
    "SMS": 0x0046,
    "AMAP": 0x0047,
    "NAVIGATION": 0x0048,
    "SPORTS_LACTATE": 0x0049,
    "BLOOD_PRESSURE_RESEARCH": 0x004A,
    "AF_RESEARCH": 0x004B,
    "SLEEP_RESEARCH": 0x004C,
    "NS_CONTROLLER": 0x004D,
    "WALKIE_TALKIE": 0x004E,
    "CONTROL_CENTER": 0x004F,
    "CTA_TOOL": 0x0050,
    "RESEARCH": 0x0051,
    "FUSION_CENTER": 0x0052,
    "CAR_CONTROL": 0x0053,
    "AI_WATCHFACE": 0x0054,
    "CHECKUP": 0x0055,
    "HEALTH_RESEARCH": 0x0056,
    "TODAY_HEALTH": 0x0057,
    "WF_AUTOTEST": 0x0058,
    "ACCESSORY_SPEAKER": 0x0059,
    "DOORLOCK": 0x005A,
    "FINDMY": 0x005B,
    "OSA_SCREENING": 0x005C,
    "CALORIE": 0x005D,
    "UV": 0x005E,
    "HEALTH_SUMMARY": 0x005F,
    "WF_JUMP_APP": 0x00FF,
    "OFFLOAD": 0x1000,
}

# Create reverse mapping: appid -> app name
APP_ID_TO_NAME: Dict[int, str] = {v: k for k, v in APP_NAME_TO_ID.items()}


class BaseAnalyzer:
    """Base class for log analyzers - extensible framework"""

    def __init__(self, name: str):
        self.name = name
        self.entries: List = []

    def parse_line(self, line: str) -> Optional:
        """Parse a single log line. Override in subclass."""
        raise NotImplementedError

    def analyze(self, file_path: str) -> List:
        """Analyze log file and return entries"""
        self.entries = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    entry = self.parse_line(line)
                    if entry:
                        self.entries.append(entry)
        except FileNotFoundError:
            print(f"Error: File {file_path} not found")
        except Exception as e:
            print(f"Error: Exception occurred while reading file - {e}")
        return self.entries

    def print_entries(self):
        """Print all parsed entries. Override in subclass."""
        raise NotImplementedError

    def print_summary(self):
        """Print statistics summary. Override in subclass."""
        raise NotImplementedError

    def export_to_csv(self, output_file: str = "log_analysis.csv"):
        """Export results to CSV file. Override in subclass."""
        raise NotImplementedError

    def export_to_html(self, output_file: str = "log_analysis.html"):
        """Export results to HTML file. Override in subclass."""
        raise NotImplementedError


class LogEntry:
    """Log entry class"""

    def __init__(self, timestamp: str, app_id: int, page_id: int, raw_line: str):
        self.timestamp = timestamp
        self.app_id = app_id
        self.page_id = page_id
        self.raw_line = raw_line
        self.app_name = APP_ID_TO_NAME.get(app_id, f"Unknown(appid={app_id})")

    def __str__(self):
        return f"[{self.timestamp}] App = 0x{self.app_id:04X}, Page = {self.page_id:2d}, Name = {self.app_name}"


class ScreenStateEntry:
    """Screen state log entry class"""

    def __init__(
        self, timestamp: str, from_state: str, to_state: str, source: str, raw_line: str
    ):
        self.timestamp = timestamp
        self.from_state = from_state
        self.to_state = to_state
        self.source = source
        self.raw_line = raw_line

    def __str__(self):
        return f"[{self.timestamp}] Screen State: {self.from_state:3s} --> {self.to_state:3s}, Source: {self.source}"


class AppIDAnalyzer(BaseAnalyzer):
    """Analyzer for AppID and PageID information from on_ui_create logs"""

    def __init__(self):
        super().__init__("AppIDAnalyzer")

    def parse_line(self, line: str) -> Optional[LogEntry]:
        """
        Parse a single log line

        Args:
            line: Log line

        Returns:
            LogEntry object, or None if not an on_ui_create log
        """
        # Match format: [01/02 04:23:33] [59] [ap] [pagemanager] on_ui_create: create view 0x18ac02b0:{15, 5}
        pattern = r"\[(\d{2}/\d{2} \d{2}:\d{2}:\d{2})\].*on_ui_create: create view 0x[0-9a-fA-F]+:\{(\d+),\s*(\d+)\}"
        match = re.search(pattern, line)

        if match:
            timestamp = match.group(1)
            app_id = int(match.group(2))
            page_id = int(match.group(3))
            return LogEntry(timestamp, app_id, page_id, line.strip())

        return None

    def print_entries(self):
        """Print all parsed log entries"""
        if not self.entries:
            print("No on_ui_create logs found")
            return

        print(f"\nFound {len(self.entries)} on_ui_create logs:\n")
        print("=" * 80)
        for i, entry in enumerate(self.entries, 1):
            print(f"{i:3d}. {entry}")
        print("=" * 80)

    def print_summary(self):
        """Print statistics summary"""
        if not self.entries:
            return

        print("\n\nStatistics Summary:")
        print("=" * 80)

        # Count by appid
        app_stats: Dict[int, int] = {}
        for entry in self.entries:
            app_stats[entry.app_id] = app_stats.get(entry.app_id, 0) + 1

        print("\nStatistics by App ID:")
        for app_id, count in sorted(app_stats.items()):
            app_name = APP_ID_TO_NAME.get(app_id, f"Unknown(appid={app_id})")
            print(f"  {app_name}: {count} times")

        # Time range
        print(
            f"\nTime range: {self.entries[0].timestamp} ~ {self.entries[-1].timestamp}"
        )
        print("=" * 80)

    def export_to_csv(self, output_file: str = "log_analysis.csv"):
        """
        Export results to CSV file

        Args:
            output_file: Output file name
        """
        if not self.entries:
            print("No data to export")
            return

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("Timestamp,AppID,PageID,AppName\n")
                for entry in self.entries:
                    # Remove MI_ prefix for display
                    display_name = (
                        entry.app_name.replace("MI_", "")
                        if entry.app_name.startswith("MI_")
                        else entry.app_name
                    )
                    f.write(
                        f"{entry.timestamp},{entry.app_id},{entry.page_id},{display_name}\n"
                    )
            print(f"\nResults exported to: {output_file}")
        except Exception as e:
            print(f"CSV export failed: {e}")

    def export_to_html(self, output_file: str = "log_analysis.html"):
        """
        Export results to HTML file with interactive table

        Args:
            output_file: Output file name
        """
        if not self.entries:
            print("No data to export")
            return

        try:
            # Calculate statistics
            run_apps = len(set(entry.app_id for entry in self.entries))
            time_start = self.entries[0].timestamp if self.entries else "N/A"
            time_end = self.entries[-1].timestamp if self.entries else "N/A"

            # Calculate time duration
            time_duration = "N/A"
            if self.entries and time_start != "N/A" and time_end != "N/A":
                try:
                    from datetime import datetime

                    start_dt = datetime.strptime(time_start, "%m/%d %H:%M:%S")
                    end_dt = datetime.strptime(time_end, "%m/%d %H:%M:%S")
                    duration = end_dt - start_dt
                    total_seconds = int(duration.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    time_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                except:
                    time_duration = "N/A"

            # Generate table rows
            rows = ""
            for i, entry in enumerate(self.entries, 1):
                display_name = entry.app_name
                rows += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{entry.timestamp}</td>
                        <td><span class="appid">0x{entry.app_id:04X}</span></td>
                        <td><span class="pageid">{entry.page_id}</span></td>
                        <td><span class="appname">{display_name}</span></td>
                    </tr>"""

            # Find unrun apps
            run_app_ids = set(entry.app_id for entry in self.entries)
            unrun_apps = []
            for app_name, app_id in sorted(APP_NAME_TO_ID.items()):
                if app_id not in run_app_ids:
                    unrun_apps.append({"app_id": app_id, "app_name": app_name})

            return {
                "total": len(self.entries),
                "run_apps": run_apps,
                "time_start": time_start,
                "time_end": time_end,
                "time_duration": time_duration,
                "rows": rows,
                "unrun_apps": unrun_apps,
            }
        except Exception as e:
            print(f"HTML data generation failed: {e}")
            return None


# Legacy functions for backward compatibility
def parse_log_line(line: str) -> Optional[LogEntry]:
    """Legacy function - use AppIDAnalyzer.parse_line instead"""
    analyzer = AppIDAnalyzer()
    return analyzer.parse_line(line)


def parse_log_file(file_path: str) -> List[LogEntry]:
    """Legacy function - use AppIDAnalyzer.analyze instead"""
    analyzer = AppIDAnalyzer()
    return analyzer.analyze(file_path)


def print_entries(entries: List[LogEntry]):
    """Legacy function - use AppIDAnalyzer.print_entries instead"""
    analyzer = AppIDAnalyzer()
    analyzer.entries = entries
    analyzer.print_entries()


def print_summary(entries: List[LogEntry]):
    """Legacy function - use AppIDAnalyzer.print_summary instead"""
    analyzer = AppIDAnalyzer()
    analyzer.entries = entries
    analyzer.print_summary()


def export_to_csv(entries: List[LogEntry], output_file: str = "log_analysis.csv"):
    """Legacy function - use AppIDAnalyzer.export_to_csv instead"""
    analyzer = AppIDAnalyzer()
    analyzer.entries = entries
    analyzer.export_to_csv(output_file)


class ScreenStateAnalyzer(BaseAnalyzer):
    """Analyzer for screen state changes from MiWearScreen logs"""

    def __init__(self):
        super().__init__("ScreenStateAnalyzer")

    def parse_line(self, line: str) -> Optional[ScreenStateEntry]:
        """
        Parse a single log line for screen state changes

        Args:
            line: Log line

        Returns:
            ScreenStateEntry object, or None if not a screen state change log
        """
        # Match format: [01/02 05:51:19] [59] [ap] [MiWearScreen] async_apply_screen_state_change: Screen state: ON-->OFF, source: TOUCH_PALM
        pattern = r"\[(\d{2}/\d{2} \d{2}:\d{2}:\d{2})\].*async_apply_screen_state_change: Screen state: (\w+)-->(\w+), source: (\w+)"
        match = re.search(pattern, line)

        if match:
            timestamp = match.group(1)
            from_state = match.group(2)
            to_state = match.group(3)
            source = match.group(4)
            return ScreenStateEntry(
                timestamp, from_state, to_state, source, line.strip()
            )

        return None

    def print_entries(self):
        """Print all parsed screen state entries"""
        if not self.entries:
            print("No screen state change logs found")
            return

        print(f"\nFound {len(self.entries)} screen state change logs:\n")
        print("=" * 80)
        for i, entry in enumerate(self.entries, 1):
            print(f"{i:3d}. {entry}")
        print("=" * 80)

    def print_summary(self):
        """Print statistics summary"""
        if not self.entries:
            return

        print("\n\nStatistics Summary:")
        print("=" * 80)

        # Count by state transition
        transition_stats: Dict[str, int] = {}
        for entry in self.entries:
            transition = f"{entry.from_state}-->{entry.to_state}"
            transition_stats[transition] = transition_stats.get(transition, 0) + 1

        print("\nStatistics by State Transition:")
        for transition, count in sorted(transition_stats.items()):
            print(f"  {transition}: {count} times")

        # Count by source
        source_stats: Dict[str, int] = {}
        for entry in self.entries:
            source_stats[entry.source] = source_stats.get(entry.source, 0) + 1

        print("\nStatistics by Source:")
        for source, count in sorted(source_stats.items()):
            print(f"  {source}: {count} times")

        # Time range
        print(
            f"\nTime range: {self.entries[0].timestamp} ~ {self.entries[-1].timestamp}"
        )
        print("=" * 80)

    def export_to_csv(self, output_file: str = "screen_state_analysis.csv"):
        """
        Export results to CSV file

        Args:
            output_file: Output file name
        """
        if not self.entries:
            print("No data to export")
            return

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("Timestamp,FromState,ToState,Source\n")
                for entry in self.entries:
                    f.write(
                        f"{entry.timestamp},{entry.from_state},{entry.to_state},{entry.source}\n"
                    )
            print(f"\nResults exported to: {output_file}")
        except Exception as e:
            print(f"CSV export failed: {e}")

    def export_to_csv_append(self, output_file: str = "miwear.csv"):
        """
        Append results to existing CSV file

        Args:
            output_file: Output file name
        """
        if not self.entries:
            return

        try:
            # Check if file exists
            file_exists = False
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    file_exists = True
            except FileNotFoundError:
                pass

            with open(output_file, "a", encoding="utf-8") as f:
                # Add separator if file exists
                if file_exists:
                    f.write("\n\n")
                f.write("Screen State Analysis\n")
                f.write("Timestamp,FromState,ToState,Source\n")
                for entry in self.entries:
                    f.write(
                        f"{entry.timestamp},{entry.from_state},{entry.to_state},{entry.source}\n"
                    )
            print(f"\nScreen state data appended to: {output_file}")
        except Exception as e:
            print(f"CSV append failed: {e}")

    def export_to_html(self, output_file: str = "screen_state_analysis.html"):
        """
        Export results to HTML file with interactive table

        Args:
            output_file: Output file name
        """
        if not self.entries:
            print("No data to export")
            return

        try:
            # Calculate statistics
            on_count = sum(1 for entry in self.entries if entry.to_state == "ON")
            off_count = sum(1 for entry in self.entries if entry.to_state == "OFF")

            # Generate table rows
            rows = ""
            for i, entry in enumerate(self.entries, 1):
                from_class = "state-on" if entry.from_state == "ON" else "state-off"
                to_class = "state-on" if entry.to_state == "ON" else "state-off"
                rows += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{entry.timestamp}</td>
                        <td><span class="{from_class}">{entry.from_state}</span></td>
                        <td><span class="{to_class}">{entry.to_state}</span></td>
                        <td><span class="source">{entry.source}</span></td>
                    </tr>"""

            # Calculate time duration
            time_duration = "N/A"
            if self.entries:
                try:
                    from datetime import datetime

                    start_dt = datetime.strptime(
                        self.entries[0].timestamp, "%m/%d %H:%M:%S"
                    )
                    end_dt = datetime.strptime(
                        self.entries[-1].timestamp, "%m/%d %H:%M:%S"
                    )
                    duration = end_dt - start_dt
                    total_seconds = int(duration.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    time_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                except:
                    time_duration = "N/A"

            return {
                "total": len(self.entries),
                "on_count": on_count,
                "off_count": off_count,
                "rows": rows,
                "time_start": self.entries[0].timestamp if self.entries else "N/A",
                "time_end": self.entries[-1].timestamp if self.entries else "N/A",
                "time_duration": time_duration,
            }
        except Exception as e:
            print(f"HTML data generation failed: {e}")
            return None


def generate_unified_html(appid_data, screen_data, output_file: str):
    """Generate unified HTML with tabs for both analyzers"""
    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Log Analysis - MiWear</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        .tabs {
            display: flex;
            background: #f8f9fa;
            border-bottom: 2px solid #e0e0e0;
        }
        .tab {
            flex: 1;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            font-weight: 600;
            font-size: 16px;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }
        .tab:hover {
            background: #e9ecef;
        }
        .tab.active {
            border-bottom-color: #667eea;
            color: #667eea;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 150px;
            height: 150px;
        }
        .stat-card h3 {
            color: #667eea;
            font-size: 32px;
            margin-bottom: 10px;
            line-height: 1.2;
        }
        .stat-card p {
            color: #666;
            font-size: 14px;
            margin: 0;
        }
        .table-container {
            padding: 30px;
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        thead {
            background: #667eea;
            color: white;
        }
        th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
        }
        tbody tr {
            border-bottom: 1px solid #e0e0e0;
            transition: background 0.2s;
        }
        tbody tr:hover {
            background: #f0f4ff;
        }
        td {
            padding: 12px 15px;
            font-size: 14px;
        }
        .appid {
            font-family: 'Courier New', monospace;
            background: #e3f2fd;
            color: #1976d2;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
        }
        .pageid {
            font-family: 'Courier New', monospace;
            background: #fff3e0;
            color: #f57c00;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
        }
        .appname {
            font-weight: 500;
            color: #333;
        }
        .state-on {
            background: #e8f5e9;
            color: #2e7d32;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 600;
        }
        .state-off {
            background: #ffebee;
            color: #c62828;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 600;
        }
        .source {
            font-weight: 500;
            color: #333;
        }
        .search-box {
            padding: 20px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }
        .search-box input {
            width: 100%;
            max-width: 400px;
            padding: 12px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .search-box input:focus {
            outline: none;
            border-color: #667eea;
        }
        .search-result {
            margin-top: 10px;
            padding: 10px 15px;
            background: #e3f2fd;
            border-radius: 8px;
            color: #1976d2;
            font-size: 14px;
            font-weight: 500;
        }
        .unrun-section {
            padding: 30px;
            background: #fff3e0;
        }
        .unrun-section h3 {
            color: #f57c00;
            font-size: 20px;
            margin-bottom: 20px;
        }
        .unrun-table {
            width: 100%;
            max-width: 1200px;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            table-layout: fixed;
        }
        .unrun-table thead {
            background: #f57c00;
            color: white;
        }
        .unrun-table th {
            padding: 12px 15px;
            text-align: center;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
        }
        .unrun-table tbody tr {
            border-bottom: 1px solid #ffe0b2;
            transition: background 0.2s;
        }
        .unrun-table tbody tr:hover {
            background: #fff8e1;
        }
        .unrun-table td {
            padding: 10px 15px;
            font-size: 14px;
            text-align: center;
        }
        .unrun-table .index {
            font-weight: 600;
            color: #f57c00;
            text-align: center;
            width: 200px !important;
        }
        .unrun-table .appid {
            font-family: 'Courier New', monospace;
            background: #ffebee;
            color: #c62828;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
            width: 500px !important;
            text-align: center;
        }
        .unrun-table .appname {
            font-weight: 500;
            color: #333;
            text-align: center;
        }
        .footer {
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 12px;
            background: #f8f9fa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Log Analysis - MiWear</h1>
            <p>Interactive visualization of log data</p>
        </div>
        <div class="tabs">
            <div class="tab active" onclick="switchTab('appid')">📱 AppID Analysis</div>
            <div class="tab" onclick="switchTab('screen')">🖥️ Screen State</div>
        </div>

        <!-- AppID Tab -->
        <div id="appid-content" class="tab-content active">
            <div class="unrun-section">
                <h3>📋 Unrun Applications ({unrun_count})</h3>
                <table class="unrun-table">
                    <thead>
                        <tr>
                            <th style="width: 200px;">#</th>
                            <th style="width: 500px;">AppID</th>
                            <th>App Name</th>
                        </tr>
                    </thead>
                    <tbody>
                        {unrun_apps}
                    </tbody>
                </table>
            </div>
            <div class="stats">
                <div class="stat-card">
                    <h3>{appid_total}</h3>
                    <p>Total</p>
                </div>
                <div class="stat-card">
                    <h3>{appid_run_apps} / {appid_total_apps}</h3>
                    <p>Run Apps Statics: Run / Total</p>
                </div>
                <div class="stat-card">
                    <h3>{appid_time_range}</h3>
                    <p>Time Range (Total Run: {appid_time_duration})</p>
                </div>
            </div>
            <div class="search-box">
                <input type="text" id="searchAppid" placeholder="🔍 Search by AppID, PageID, or App Name..." onkeyup="filterTable('appid')">
                <div id="searchResultAppid" class="search-result" style="display: none;"></div>
            </div>
            <div class="table-container">
                <table id="appidTable">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Timestamps</th>
                            <th>AppID</th>
                            <th>PageID</th>
                            <th>App Name</th>
                        </tr>
                    </thead>
                    <tbody>
                        {appid_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Screen State Tab -->
        <div id="screen-content" class="tab-content">
            <div class="stats">
                <div class="stat-card">
                    <h3>{screen_total}</h3>
                    <p>Total</p>
                </div>
                <div class="stat-card">
                    <h3>{screen_on} / {screen_off}</h3>
                    <p>ON / OFF</p>
                </div>
                <div class="stat-card">
                    <h3>{screen_time_range}</h3>
                    <p>Time Range (Total Run: {screen_time_duration})</p>
                </div>
            </div>
            <div class="search-box">
                <input type="text" id="searchScreen" placeholder="🔍 Search by state or source..." onkeyup="filterTable('screen')">
                <div id="searchResultScreen" class="search-result" style="display: none;"></div>
            </div>
            <div class="table-container">
                <table id="screenTable">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Timestamps</th>
                            <th>From</th>
                            <th>To</th>
                            <th>Source</th>
                        </tr>
                    </thead>
                    <tbody>
                        {screen_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="footer">
            Generated by MiWear Log Analyzer | Click on table headers to sort
        </div>
    </div>
    <script>
        function switchTab(tabName) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(function(content) {
                content.classList.remove('active');
            });

            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(function(tab) {
                tab.classList.remove('active');
            });

            // Show selected tab content
            document.getElementById(tabName + '-content').classList.add('active');

            // Add active class to selected tab
            event.target.classList.add('active');
        }

        function filterTable(tableType) {
            var inputId = tableType === 'appid' ? 'searchAppid' : 'searchScreen';
            var tableId = tableType === 'appid' ? 'appidTable' : 'screenTable';
            var resultId = tableType === 'appid' ? 'searchResultAppid' : 'searchResultScreen';

            var input, filter, table, tr, td, i, txtValue;
            input = document.getElementById(inputId);
            filter = input.value.toUpperCase();
            table = document.getElementById(tableId);
            tr = table.getElementsByTagName("tr");

            var visibleCount = 0;
            for (i = 1; i < tr.length; i++) {
                var found = false;
                var tds = tr[i].getElementsByTagName("td");
                for (var j = 0; j < tds.length; j++) {
                    if (tds[j]) {
                        txtValue = tds[j].textContent || tds[j].innerText;
                        if (txtValue.toUpperCase().indexOf(filter) > -1) {
                            found = true;
                            break;
                        }
                    }
                }
                tr[i].style.display = found ? "" : "none";
                if (found) {
                    visibleCount++;
                }
            }

            // Update search result display
            var resultDiv = document.getElementById(resultId);
            if (filter.length > 0) {
                resultDiv.style.display = 'block';
                resultDiv.textContent = 'Found ' + visibleCount + ' matched';
            } else {
                resultDiv.style.display = 'none';
            }
        }

        // Sort table on header click
        var sortDirection = {};
        document.querySelectorAll('th').forEach(function(th, index) {
            if (index > 0) {  // Skip the # column
                th.style.cursor = 'pointer';
                th.onclick = function() {
                    var table = th.closest('table');
                    var rows = Array.from(table.querySelectorAll('tbody tr'));
                    var colIndex = Array.from(th.parentNode.children).indexOf(th);

                    sortDirection[colIndex] = !sortDirection[colIndex];

                    rows.sort(function(a, b) {
                        var aVal = a.children[colIndex].textContent.trim();
                        var bVal = b.children[colIndex].textContent.trim();

                        if (sortDirection[colIndex]) {
                            return aVal.localeCompare(bVal);
                        } else {
                            return bVal.localeCompare(aVal);
                        }
                    });

                    rows.forEach(function(row) {
                        table.querySelector('tbody').appendChild(row);
                    });
                };
            }
        });
    </script>
</body>
</html>"""

    # Replace placeholders
    html_content = html_template.replace("{appid_total}", str(appid_data["total"]))
    html_content = html_content.replace("{appid_run_apps}", str(appid_data["run_apps"]))
    html_content = html_content.replace("{appid_total_apps}", str(len(APP_NAME_TO_ID)))
    html_content = html_content.replace(
        "{appid_time_range}", f"{appid_data['time_start']}<br>{appid_data['time_end']}"
    )
    html_content = html_content.replace(
        "{appid_time_duration}", appid_data.get("time_duration", "N/A")
    )
    html_content = html_content.replace("{appid_rows}", appid_data["rows"])

    # Generate unrun apps HTML
    unrun_apps_html = ""
    for i, app in enumerate(appid_data["unrun_apps"], 1):
        unrun_apps_html += f"""
            <tr>
                <td class="index">{i}</td>
                <td class="appid">0x{app['app_id']:04X}</td>
                <td class="appname">{app['app_name']}</td>
            </tr>"""

    html_content = html_content.replace(
        "{unrun_count}", str(len(appid_data["unrun_apps"]))
    )
    html_content = html_content.replace("{unrun_apps}", unrun_apps_html)

    html_content = html_content.replace("{screen_total}", str(screen_data["total"]))
    html_content = html_content.replace("{screen_on}", str(screen_data["on_count"]))
    html_content = html_content.replace("{screen_off}", str(screen_data["off_count"]))
    html_content = html_content.replace(
        "{screen_time_range}",
        f"{screen_data.get('time_start', 'N/A')}<br>{screen_data.get('time_end', 'N/A')}",
    )
    html_content = html_content.replace(
        "{screen_time_duration}", screen_data.get("time_duration", "N/A")
    )
    html_content = html_content.replace("{screen_rows}", screen_data["rows"])

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\nResults exported to: {output_file}")
    print(f"Open {output_file} in your browser to view the interactive report")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Log analyzer for MiWear - extensible framework for analyzing various log patterns"
    )
    parser.add_argument(
        "-f",
        "--file",
        default="1.log",
        help="Log file path (default: 1.log)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="miwear.csv",
        help="Output CSV file path (default: miwear.csv)",
    )
    parser.add_argument(
        "-t",
        "--type",
        choices=["appid", "screen", "all"],
        default="all",
        help="Analyzer type: appid, screen, or all (default: all)",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Export results to HTML format (interactive web page)",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open HTML file in browser after generation",
    )
    args = parser.parse_args()

    log_file = args.file
    output_file = args.output
    analyzer_type = args.type
    export_html = args.html
    open_browser = args.open_browser

    print("Starting log parsing...")
    print(f"Log file: {log_file}")
    print(f"Analyzer type: {analyzer_type}")
    print(f"Export format: {'HTML' if export_html else 'CSV'}")

    # Run selected analyzers
    appid_data = None
    screen_data = None

    if analyzer_type in ["appid", "all"]:
        print("\n" + "=" * 80)
        print("Running AppID Analyzer")
        print("=" * 80)
        appid_analyzer = AppIDAnalyzer()
        appid_entries = appid_analyzer.analyze(log_file)
        appid_analyzer.print_entries()
        appid_analyzer.print_summary()

        if export_html:
            appid_data = appid_analyzer.export_to_html("")
        else:
            appid_analyzer.export_to_csv(output_file)

        # Prompt for unknown appids
        unknown_app_ids = [
            entry.app_id
            for entry in appid_entries
            if entry.app_name.startswith("Unknown")
        ]
        if unknown_app_ids:
            print(
                "\nNote: The following appids were not found in the mapping table:",
                sorted(set(unknown_app_ids)),
            )

    if analyzer_type in ["screen", "all"]:
        print("\n" + "=" * 80)
        print("Running Screen State Analyzer")
        print("=" * 80)
        screen_analyzer = ScreenStateAnalyzer()
        screen_analyzer.analyze(log_file)
        screen_analyzer.print_entries()
        screen_analyzer.print_summary()

        if export_html:
            screen_data = screen_analyzer.export_to_html("")
        else:
            # Append to the same CSV file
            screen_analyzer.export_to_csv_append(output_file)

    # Generate unified HTML if both analyzers ran
    if export_html and analyzer_type == "all" and appid_data and screen_data:
        html_output = output_file.replace(".csv", ".html")
        generate_unified_html(appid_data, screen_data, html_output)
        # Open HTML file in browser if requested
        if open_browser:
            html_path = os.path.abspath(html_output)
            print(f"\nOpening {html_output} in your browser...")
            webbrowser.open(f"file://{html_path}")
    elif export_html and analyzer_type == "appid" and appid_data:
        print("\nNote: Use -t all to generate unified HTML with both analyzers")
    elif export_html and analyzer_type == "screen" and screen_data:
        print("\nNote: Use -t all to generate unified HTML with both analyzers")

    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
