#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Package for GUI backends of the SAJE project
"""

from . import tkinter

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Quentin Soubeyran"
__status__ = "alpha"


BACKENDS = {
    "tkinter": tkinter
}

DEFAULT = "tkinter"