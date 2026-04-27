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

from typing import Dict

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

# Reverse mapping: appid -> app name
APP_ID_TO_NAME: Dict[int, str] = {v: k for k, v in APP_NAME_TO_ID.items()}
