#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility module for the SAJE project
"""

# Built-in modules
from traceback import format_exception_only
# Thrid party modules

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Quentin Soubeyran"
__status__ = "alpha"

def err_str(err):
    """
    Utility function to get a nice str of an Exception for display purposes
    """
    return "\n".join(format_exception_only(type(err), err))