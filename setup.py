#!/usr/bin/env python3
# -*- coding:UTF-8 -*-
#
# Copyright (C) 2025 Junbo Zheng. All rights reserved.
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

import os
from setuptools import setup


def get_version():
    here = os.path.abspath(os.path.dirname(__file__))
    init_path = os.path.join(here, "miwear", "__init__.py")
    with open(init_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip("\"'")
    raise RuntimeError("Unable to find version string in __init__.py!")


setup(
    name="miwear",
    version=get_version(),
    description="Python Miwear tools for extracting and handling archives/logs",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Junbo Zheng",
    author_email="3273070@qq.com",
    url="https://github.com/Junbo-Zheng/miwear",
    packages=["miwear"],
    python_requires=">=3.7",
    license="Apache-2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    install_requires=[],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "miwear_log = miwear.log:main",
            "miwear_gz = miwear.gz:main",
            "miwear_tz = miwear.targz:main",
            "miwear_uz = miwear.unzip:main",
            "miwear_assert = miwear.assert:main",
        ],
    },
)
