#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility module for the SAJE project
"""

# Built-in modules
from traceback import format_exception_only

# Thrid party modules

# Local modules
from . import version

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = version.__version__
__maintainer__ = "Quentin Soubeyran"
__status__ = version.__status__


def err_str(err):
    """
    Utility function to get a nice str of an Exception for display purposes
    """
    return "\n".join(format_exception_only(type(err), err))