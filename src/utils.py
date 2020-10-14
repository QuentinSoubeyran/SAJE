#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility module for the SAJE project
"""

from traceback import format_exception_only

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


class NocaseList(list):
    def __contains__(self, value):
        if isinstance(value, str):
            return super().__contains__(value.lower())
        return super().__contains__(value)
