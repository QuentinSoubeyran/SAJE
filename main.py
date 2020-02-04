#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GUI program to search in JSON-formatted simple databases
"""
# Built-in modules
import json
import traceback
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog
import tkinter.messagebox
from pathlib import Path
from collections import namedtuple
from string import Formatter
from datetime import datetime

# Thrid party modules
import tk_html_widgets as tk_html
from dotmap import DotMap

# Local modules
import src.jsondb as jsondb
import src.jsonpp as jsonpp

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Quentin Soubeyran"
__status__ = "alpha"

# Constants
DEFAULT_SIZE = (640, 480)  # width, height
ANY_VALUE = "--Any--"

ParsedFile = namedtuple("ParsedFile", ["database", "display_string", "fields_geometry"])

class SearchCallback:
    """
    Class to search in the database when the search button is pressed
    """

    CACHE_KEY = "__CACHED_DISPLAY_STRING__"

    def __init__(self, db, gui_dict, display, display_string):
        self.db = db
        self.gui_dict = gui_dict
        self.display = display
        self.display_string = display_string

    def get_display(self, json_obj, display_string):
        if self.CACHE_KEY not in json_obj:
            # TODO: add support for optional keys
            if display_string is not None:
                json_obj[self.CACHE_KEY] = display_string.format(
                    **{".".join(key): value for key, value in jsonpp.flatten(json_obj)}
                )
            else:
                json_obj[self.CACHE_KEY] = json.dumps(json_obj, indent=2)
        return json_obj[self.CACHE_KEY]

    def get_option_args(self, field: jsondb.OptionField, field_gui_container):
        args = {"accept_missing": bool(field_gui_container.accept_na_var.get())}
        if field.multi_selection:
            selected = field_gui_container.selector.selection()
            if not selected:
                return None
            args["value_or_set"] = selected
        else:
            value = field_gui_container.variable.get()
            if value == ANY_VALUE:
                return None
            args["value_or_set"] = value
        return args

    def get_integer_args(self, field: jsondb.IntegerField, field_gui_container):
        value = field_gui_container.selector.get()
        if value == ANY_VALUE:
            return None
        value = field.bounded_value(int(value))
        field_gui_container.selector.set(value)
        return {
            "accept_missing": bool(field_gui_container.accept_na_var.get()),
            "value": value,
        }

    def get_text_args(self, field, field_gui_container):
        text = field_gui_container.selector.get("1.0", "end-1c")
        values = [s for s in text.split("\n") if s]
        if not values:
            return None
        return {
            "accept_missing": bool(field_gui_container.accept_na_var.get()),
            "operator": field_gui_container.operator_selector.get(),
            "value": values,
        }

    def __call__(self):
        try:
            search_args = {}
            for field_name, field_gui in self.gui_dict.items():
                field = self.db.fields[field_name]
                get_args_method = getattr(self, "get_%s_args" % field.TYPE.lower())
                args = get_args_method(field, field_gui)
                if args is not None:
                    search_args[field_name] = args
            print("SEARCHING with arguments:\n")
            print(search_args)
            results = self.db.search(criteria=search_args)
            self.display.set_html(
                html="\n\n".join(
                    self.get_display(result, self.display_string) for result in results
                )
                + "\ndone at %s" % datetime.now(),
                strip=False,
            )
        except Exception as err:
            traceback.print_tb(err.__traceback__)
            tk.messagebox.showerror(title="Error",)


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Search in Arbitrary Json Engine")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.menu = tk.Menu(self)
        self.menu.add_command(label="Open file", command=self.open_file)
        self.config(menu=self.menu)

        self.notebook = ttk.Notebook(self)
        self.tabs = []
        self.notebook.grid(column=0, row=0, sticky="nsew")

        self.open_dir_cache = "."
        self.file_cache = {}

    def open_file(self):
        path = tk.filedialog.askopenfilename(
            initialdir=self.open_dir_cache,
            title="Open file",
            filetypes=(("JSON files", "*.json"), ("all files", "*.*")),
        )
        if not path:
            return
        path = Path(path)
        self.open_dir_cache = str(path.parent)
        try:
            with path.open("r") as f:
                json_file = json.load(f)
        except Exception as err:
            print(traceback.print_tb(err.__traceback__))
            tk.messagebox.showerror(
                title="Open file",
                message="Couldn't read file. Is it a JSON ? Error:\n%s" % err,
            )
            return
        file_id = str(path.absolute())
        if file_id not in self.file_cache:
            try:
                self.file_cache[file_id] = self.parse_json(json_file)
            except Exception as err:
                print(traceback.print_tb(err.__traceback__))
                tk.messagebox.showerror(
                    title="Open file",
                    message="Error encountered while parsing file:\n%s" % err,
                )
                return
        parsed_file = self.file_cache[file_id]
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

    def parse_json(self, json_file):
        fields_geometry = []
        fields = {}
        for json_obj in json_file["fields"]:
            if jsonpp.Type.of(json_obj) is jsonpp.Type.Object:
                name = json_obj["name"]
                fields_geometry.append(name)
                if name not in fields:
                    fields[name] = {
                        key: value
                        for key, value in json_obj.items()
                        if key not in ("name",)
                    }
                else:
                    raise NameError("Duplicated field name %s" % name)
            elif jsonpp.Type.of(json_obj) is jsonpp.Type.Array:
                sub_geometry = []
                for json_obj_sub in json_obj:
                    name = json_obj_sub["name"]
                    sub_geometry.append(name)
                    if name not in fields:
                        fields[name] = {
                            key: value
                            for key, value in json_obj_sub.items()
                            if key not in ("name",)
                        }
                    else:
                        raise NameError("Duplicated field name %s" % name)
                fields_geometry.append(sub_geometry)
        database = jsondb.Database.from_json(
            {"data": json_file["data"], "fields": fields}
        )
        display_string = json_file.get("display_string")
        if display_string and jsonpp.Type.of(display_string) is jsonpp.Type.Array:
            display_string = "".join(display_string)
        return ParsedFile(
            database=database,
            display_string=display_string,
            fields_geometry=fields_geometry,
        )

    def make_tab(self, parsed_file):
        container = DotMap()
        container.tab = ttk.Frame(master=self.notebook)
        container.search = ttk.Frame(master=container.tab)
        container.result = ttk.Frame(master=container.tab)
        container.search.pack(side="left", expand=True, fill="y")
        container.result.pack(side="right", expand=True, fill="both")
        # result part
        container.display = tk_html.HTMLScrolledText(
            master=container.result, wrap="word"
        )
        container.display.pack(side="left", expand=True, fill="both")
        # Search part
        container.search_button = ttk.Button(master=container.search, text="Search")
        container.search_button.pack(side="top")
        container.field_gui_dict = self.make_search_frame(
            parsed_file=parsed_file,
            field_gui_dict={},
            master_frame=container.search,
            pack_side="top",
            nested_list=parsed_file.fields_geometry,
        )
        container.search_button.configure(
            command=SearchCallback(
                db=parsed_file.database,
                gui_dict=container.field_gui_dict,
                display=container.display,
                display_string=parsed_file.display_string,
            )
        )
        return container

    def make_search_frame(
        self, parsed_file, field_gui_dict, master_frame, pack_side, nested_list
    ):
        for element in nested_list:
            if isinstance(element, list):
                sub_frame = ttk.Frame(master=master_frame)
                self.make_search_frame(
                    parsed_file=parsed_file,
                    field_gui_dict=field_gui_dict,
                    master_frame=sub_frame,
                    pack_side="top" if pack_side == "left" else "left",
                    nested_list=element,
                )
                sub_frame.pack(
                    side=pack_side,
                    expand=True,
                    # fill="y" if pack_side == "left" else "x",
                )
            else:
                field_name = element
                field = parsed_file.database.fields[field_name]
                try:
                    make_method = getattr(self, "make_%s_GUI" % field.TYPE.lower())
                except AttributeError:
                    tk.messagebox.showerror(
                        title="Error",
                        message="No GUI found for search field of type %s" % field.TYPE,
                    )
                field_gui_container = make_method(
                    master=master_frame, name=field_name, field=field
                )
                field_gui_container.frame.pack(
                    side=pack_side,
                    expand=True,
                    # fill="y" if pack_side == "left" else "x",
                )
                field_gui_dict[field_name] = field_gui_container
        return field_gui_dict

    def make_option_GUI(self, master, name, field: jsondb.OptionField):
        container = DotMap()
        container.frame = ttk.Frame(master=master)
        container.label = ttk.Label(container.frame, text=name)
        container.label.pack(side="top", fill="x")
        container.accept_na_var = tk.IntVar(container.frame, value=True)
        container.accept_na_button = ttk.Checkbutton(
            master=container.frame,
            text="accept N/A",
            onvalue=1,
            offvalue=0,
            variable=container.accept_na_var,
        )
        container.accept_na_var.set(1)
        container.accept_na_button.pack(side="top", expand=True)

        if field.multi_selection:
            container.selector = ttk.Treeview(
                master=container.frame,
                columns=[],
                height=min(7, len(field.values)),
                show="tree",
            )
            container.selector.column("#0", width=35)
            container.scrollbar = ttk.Scrollbar(
                container.frame, orient=tk.VERTICAL, command=container.selector.yview
            )
            container.selector.configure(yscrollcommand=container.scrollbar.set)
            container.scrollbar.pack(side="right", fill="y")
            container.selector.pack(side="left", fill="both", expand=True)
        else:
            values = sorted(field.values.copy())
            if field.optional:
                values = [ANY_VALUE] + values
            container.variable = tk.StringVar(container.frame, value=values[0])
            container.selector = ttk.OptionMenu(
                container.frame, container.variable, values[0], *values
            )
            container.selector.pack(side="bottom", fill="both", expand=True)
        return container

    def make_integer_GUI(self, master, name, field: jsondb.IntegerField):
        container = DotMap()
        container.frame = ttk.Frame(master=master)
        container.label = ttk.Label(container.frame, text=name)
        container.label.pack(side="top", fill="x")
        # missing value acceptation
        container.accept_na_var = tk.IntVar(container.frame, value=True)
        container.accept_na_button = ttk.Checkbutton(
            master=container.frame,
            text="accept N/A",
            onvalue=1,
            offvalue=0,
            variable=container.accept_na_var,
        )
        container.accept_na_var.set(1)
        container.accept_na_button.pack(side="top", expand=True)
        # integer selection
        values = list(field.listed)
        if field.optional:
            values = [ANY_VALUE] + values
        container.selector = ttk.Combobox(master=container.frame, values=values)
        if field.optional:
            container.selector.set(ANY_VALUE)
        else:
            container.selector.set(field.min_ or field.max_ or 0)
        container.selector.pack(side="bottom", fill="both", expand=True)
        return container

    def make_text_GUI(self, master, name, field: jsondb.TextField):
        container = DotMap()
        container.frame = ttk.Frame(master=master)
        container.label = ttk.Label(container.frame, text=name)
        container.label.pack(side="top", fill="x")
        # missing value acceptation and operation on lines
        container.option_frame = ttk.Frame(master=container.frame)
        container.accept_na_var = tk.IntVar(container.option_frame, value=True)
        container.accept_na_button = ttk.Checkbutton(
            master=container.option_frame,
            text="accept N/A",
            onvalue=1,
            offvalue=0,
            variable=container.accept_na_var,
        )
        container.accept_na_var.set(1)
        container.accept_na_button.pack(side="left", expand=True)
        container.operator_label = ttk.Label(
            master=container.option_frame, text="required :"
        )
        container.operator_selector = ttk.Combobox(
            master=container.option_frame, values=("any", "all"), state="readonly"
        )
        container.operator_selector.set("any")
        container.operator_label.pack(side="left")
        container.operator_selector.pack(side="left")
        container.option_frame.pack(side="top")
        # Text input
        container.selector = tk.Text(
            master=container.frame, wrap="word", height=3, width=30
        )
        container.selector.pack(side="bottom", expand=True)
        return container


if __name__ == "__main__":
    root = App()
    root.geometry(
        "%dx%d+%d+%d"
        % (
            DEFAULT_SIZE[0],
            DEFAULT_SIZE[1],
            root.winfo_screenwidth() // 2 - DEFAULT_SIZE[0] // 2,
            root.winfo_screenheight() // 2 - DEFAULT_SIZE[1] // 2,
        )
    )
    root.mainloop()
