#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Common code for GUI backend of the SAJE project

To use that module to implement a GUI backend for SAJE,
look at https://stackoverflow.com/questions/3277367/how-does-pythons-super-work-with-multiple-inheritance
to understand how the backend class can handle multiple inheritance (see backend.tkinter module)
for examples
"""

# Built-in modules
import logging
import traceback
from abc import ABC, abstractmethod

# Local modules
from .. import version
from .. import parsing
from .. import utils

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = version.__version__
__maintainer__ = "Quentin Soubeyran"
__status__ = version.__status__

LOGGER = logging.getLogger("SAJE.backend.common")


class AbstractKwargsProvider(ABC):
    @abstractmethod
    def get_kwargs(self):
        """
        Get the keywords arguments this class provides
        """
        raise NotImplementedError(
            "AbstractKwargsProvider subclasses must implement a get_kwargs() method"
        )


class AbstractHTMLDisplay(ABC):
    @abstractmethod
    def display_html(self, html):
        """
        Change the HTML display to the html argument
        """
        raise NotImplementedError(
            "AbstractHTMLDisplay subclasses must implement a display_html() method"
        )


class AbstractSearchCallback(ABC):
    """
    Callable class to handle searching a jsondb.Database object
    """

    LOGGER = LOGGER

    def __init__(
        self,
        parsed_file: parsing.ParsedFile,
        search_button: AbstractKwargsProvider,
        gui_dict,
        display: AbstractHTMLDisplay,
    ):
        self.parsed_file = parsed_file
        self.search_button = search_button
        self.gui_dict = gui_dict
        self.display = display

    @abstractmethod
    def show_error(self, title="", message=""):
        """
        Method to show an error message to the user
        """
        raise NotImplementedError(
            "SearchCallbackCommon subclasses must implement a show_error() method"
        )

    def __call__(self):
        try:
            search_args = {}
            for field_name, gui in self.gui_dict.items():
                kwargs = gui.get_kwargs()
                if kwargs is not None:
                    search_args[field_name] = kwargs
            results = self.parsed_file.database.search(
                criteria=search_args, **self.search_button.get_kwargs()
            )
            html = "\n\n".join(
                parsing.get_display(self.parsed_file.display_string, result)
                for result in results
            )
            self.display.display_html(html)
        except Exception as err:
            self.LOGGER.error(
                "Error during search:\n%s\n%s",
                "".join(traceback.format_tb(err.__traceback__)),
                utils.err_str(err),
            )
            self.show_error(
                title="Search", message="Error during search:\n%s" % utils.err_str(err)
            )


class AbstractNotebook(ABC):
    """
    Class to handle the multiple tab of the GUI
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tabs_ = []

    @abstractmethod
    def add_tab(self, tab, title=None):
        """
        Adds a tab to the notebook
        """
        raise NotImplementedError(
            "NotebookCommon subclasses must implement a add_tab() method"
        )


class AbstractMainApp(ABC):
    """
    Base class for the main App. Provides GUI utility methods
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        """
        Subclass __init__ must initialize:
            - a `notebook` attribute, instance of a Subclass of NotebookBase
        """
        if type(self) is AbstractMainApp:
            raise RuntimeError("AbstractMainApp must be subclassed")
        else:
            super().__init__(*args, **kwargs)

    @abstractmethod
    def set_title(self, title):
        """
        Set the title of the app windows
        """
        raise NotImplementedError(
            "MainAppCommon subclasses must implement a set_title() method"
        )

    @abstractmethod
    def show_error(self, title="", message=""):
        """
        Method to show an error message to the user
        """
        raise NotImplementedError(
            "MainAppCommon subclasses must implement a show_error() method"
        )

    @abstractmethod
    def ask_file(self):
        """
        Method to ask the user for a file path to open. May return None for no action
        """
        raise NotImplementedError(
            "MainAppCommon subclasses must implement a show_error() method"
        )

    @abstractmethod
    def new_tab(self, parsed_file: parsing.ParsedFile):
        """
        Method to create a new tab from a ParsedFile object
        """
        raise NotImplementedError(
            "MainAppCommon subclasses must implement a new_tab() method"
        )
    
    @abstractmethod
    def on_modes(self):
        """Adapts the display after a change of modes"""

    @abstractmethod
    def start(self):
        """
        Start the App
        """
        raise NotImplementedError(
            "MainAppCommon subclasses must implement a start() method"
        )
