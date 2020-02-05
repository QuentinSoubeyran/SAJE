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
from collections import namedtuple

# Thrid party modules


# Local modules
import src.utils as utils
import src.jsondb as jsondb
import src.jsonpp as jsonpp
import src.backends as backends

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Quentin Soubeyran"
__status__ = "alpha"

LOGGER = logging.getLogger("SAJE")
LOCAL_DIR = Path(__file__).parent
CONFIG_FILE = LOCAL_DIR / "preferences.json"
DEFAULT_PREFS = {
    "backend": backends.DEFAULT
}

# Load GUI backend preferences
if CONFIG_FILE.exists():
    try:
        with CONFIG_FILE.open("r") as f:
            PREFS = jsonpp.load(f)
    except Exception as err:
        LOGGER.error(
            "Couldn't open or parse preference file, due to:\n%s\nUsing default preferences",
            utils.err_str(err)
        )
        PREFS = DEFAULT_PREFS.copy()
else:
    PREFS = DEFAULT_PREFS.copy()
    try:
        with CONFIG_FILE.open("w") as f:
            jsonpp.dump(PREFS, f, indent=4, sort_keys=True)
    except Exception as err:
        LOGGER.error(
            "Couldn't create preference file due to:\n%s",
            utils.err_str(err)
        )

# Load the actual backend
if PREFS["backend"] not in backends.BACKENDS:
    LOGGER.error(
        "Backend '%s' is invalid, defaulting to '%s'",
        PREFS["backend"],
        backends.DEFAULT
    )
    PREFS["backend"] = backends.DEFAULT

backend = backends.BACKENDS[PREFS["backend"]]

ParsedFile = namedtuple("ParsedFile", ["database", "display_string", "fields_geometry"])

class SAJE(backend.MainAppBase):
    """
    Main SAJE App project class
    """
    def __init__(self):
        super.__init__()
        self.notebook = backend.Notebook()
        self.open_dir_cache = "."
        self.cached_files = {}
    
    def open_file(self):
        basepath = self.ask_file()
        if not basepath:
            return
        path = Path(basepath)
        self.open_dir_cache = str(path.parent)
        file_id = str(path.absolute())
        if file_id not in self.cached_files:
            try:
                with path.open("r") as f:
                    json_file = jsonpp.load(f)
            except Exception as err:
                LOGGER.error(
                    "Couldn't read file %s. Stacktrace:\n%s\n%s",
                    str(path),
                    "".join(traceback.format_tb(err.__traceback__)),
                    utils.err_str(err)
                )
                self.show_error(
                    title="Open file",
                    message="Couldn't read file: is it really JSON ?\n%s" % utils.err_str(err)
                )
                return
            try:
                self.cached_files[file_id] = self.parse_json(json_file)
            except Exception as err:
                LOGGER.error(
                    "Couldn't parse file %s. Stacktrace:\n%s\n%s",
                    str(path),
                    "".join(traceback.format_tb(err.__traceback__)),
                    utils.err_str(err)
                )
                self.show_error(
                    title="Open file",
                    message="Couldn't parse file, verify it complies with SAJE format\n%s" % utils.err_str(err)
                )
                return
        parsed_file = self.cached_files[file_id]
        try:
            container = self.make_tab(parsed_file)
        except Exception as err:
            print(traceback.print_tb(err.__traceback__))
            tk.messagebox.showerror(
                title="Open file",
                message="Error encountered while creating tab:\n%s" % err,
            )
            return
        self.tabs.append(container)
        self.notebook.add(container.tab, text=path.stem)

saje = SAJE()
saje.start()