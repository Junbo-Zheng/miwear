#!/usr/bin/env python3
# -*- coding:UTF-8 -*-
#
# Convenience wrapper so you can run: ./miwear/check.py [args]
# without installing the package.
#

import os
import sys

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miwear.check import main  # noqa: E402

main()
