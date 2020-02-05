#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Common code for GUI backend of the SAJE project
"""

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Quentin Soubeyran"
__status__ = "alpha"


class GuiBase:
    def __init__(self):
        pass

    def get_kwargs(self):
        """
        Returns the keyword-arguments specified by the GUI for the field
        """
        raise NotImplementedError("BaseGUI subclasses must implement a get_kwargs() method")


class GuiDataBase:
    """
    Base class for parsing JSON data that define both GUI elements and
    a FieldBase subclass
    """
    def __init__(self, json_obj):
        #TODO: implement shared init
        raise NotImplementedError("TODO")

    def make_gui(self):
        """
        Return a Subclass of GuiBase appropriate to the Field type
        """
        raise NotImplementedError("GuiDataBase subclasses must implement a make_gui() method")


class MainAppBase:
    """
    Base class for the main App. Provides GUI utility methods
    """
    def __init__(self):
        raise RuntimeError("MainAppBase must be subclassed")

    def set_title(self, title):
        """
        Set the title of the app windows
        """
        raise NotImplementedError("MainAppBase subclasses must implement a set_title() method")
    
    def show_error(self, title="", message=""):
        """
        Method to show an error message to the user
        """
        raise NotImplementedError("MainAppBase subclasses must implement a show_error() method")

    def ask_file(self):
        """
        Method to ask the user for a file path to open. May return None for no action
        """
        raise NotImplementedError("MainAppBase subclasses must implement a show_error() method")

    def start(self):
        """
        Start the App
        """
        raise NotImplementedError("MainAppBase subclasses must implement a start() method")
    
    
