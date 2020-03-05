#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GUI program to search in JSON-formatted simple databases
"""

# WIP version 2

# Built-in modules
import logging
import traceback
from pathlib import Path

# Local modules
import src.version as version
import src.utils as utils
import src.json_utils.jsonplus as json
import src.parsing as parsing
import src.backends as backends

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = version.__version__
__maintainer__ = "Quentin Soubeyran"
__status__ = version.__status__

LOGGER = logging.getLogger("SAJE")
LOCAL_DIR = Path(__file__).parent
CONFIG_FILE = LOCAL_DIR / "preferences.json"
DEFAULT_PREFS = {"backend": backends.DEFAULT}

# Load GUI backend preferences
if CONFIG_FILE.exists():
    try:
        with CONFIG_FILE.open("r") as f:
            PREFS = json.load(f)
    except Exception as err:
        LOGGER.error(
            "Couldn't open or parse preference file, due to:\n%s\nUsing default preferences",
            utils.err_str(err),
        )
        PREFS = DEFAULT_PREFS.copy()
else:
    PREFS = DEFAULT_PREFS.copy()
    try:
        with CONFIG_FILE.open("w") as f:
            json.dump(PREFS, f, indent=4, sort_keys=True)
    except Exception as err:
        LOGGER.error("Couldn't create preference file due to:\n%s", utils.err_str(err))

# Load the actual backend
if PREFS["backend"] not in backends.BACKENDS:
    LOGGER.error(
        "Backend '%s' is invalid, defaulting to '%s'",
        PREFS["backend"],
        backends.DEFAULT,
    )
    PREFS["backend"] = backends.DEFAULT

backend = backends.BACKENDS[PREFS["backend"]]


class SAJE(backend.MainApp):
    """
    Main SAJE App project class
    """

    def __init__(self):
        super().__init__()
        self.open_dir_cache = "."
        self.cached_files = {}

    def open_file(self):
        """
        Method for opening a file, the callback for the "open file" menu button
        Handle all parts and error display
        """
        basepath = self.ask_file()
        if not basepath:
            return
        path = Path(basepath)
        self.open_dir_cache = str(path.parent)
        file_id = str(path.absolute())
        if file_id not in self.cached_files:
            try:
                with path.open("r") as f:
                    json_file = json.load(f)
            except Exception as err:
                LOGGER.error(
                    "Couldn't read file %s. Stacktrace:\n%s\n%s",
                    str(path),
                    "".join(traceback.format_tb(err.__traceback__)),
                    utils.err_str(err),
                )
                self.show_error(
                    title="Open file",
                    message="Couldn't read file: is it really JSON ?\n%s"
                    % utils.err_str(err),
                )
                return
            try:
                self.cached_files[file_id] = parsing.parse_file(json_file, filename=path.stem)
            except Exception as err:
                LOGGER.error(
                    "Couldn't parse file %s. Stacktrace:\n%s\n%s",
                    str(path),
                    "".join(traceback.format_tb(err.__traceback__)),
                    utils.err_str(err),
                )
                self.show_error(
                    title="Open file",
                    message="Couldn't parse file, verify it complies with SAJE format\n%s"
                    % utils.err_str(err),
                )
                return
        parsed_file = self.cached_files[file_id]
        try:
            tab = self.new_tab(parsed_file)
        except Exception as err:
            LOGGER.error(
                "Couldn't create tab from file %s. Stacktrace:\n%s\n%s",
                str(path),
                "".join(traceback.format_tb(err.__traceback__)),
                utils.err_str(err),
            )
            self.show_error(
                title="Open file",
                message="Couldn't create the new tab\n%s" % utils.err_str(err),
            )
            return
        self.notebook.add_tab(tab, title=parsed_file.name)


saje = SAJE()
saje.set_title("SAJE %s (%s backend)" % (version.__version__, PREFS["backend"]))
saje.start()
