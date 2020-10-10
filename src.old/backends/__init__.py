#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Package for GUI backends of the SAJE project
"""

from .. import version
from . import tkinter

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = version.__version__
__maintainer__ = "Quentin Soubeyran"
__status__ = version.__status__


BACKENDS = {"tkinter": tkinter}

DEFAULT = "tkinter"
