#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tkinter backend for SAJE project
"""
# Built-in modules
import math
import logging
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog
import tkinter.messagebox

# Thrid party modules
import tk_html_widgets as tk_html
from dotmap import DotMap

# Local modules
from .. import version
from ..json_utils import jsondb
from .. import parsing
from ..backends import common

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = version.__version__
__maintainer__ = "Quentin Soubeyran"
__status__ = version.__status__

LOGGER = logging.getLogger("SAJE.backend.tkinter")
DEFAULT_SIZE = (640, 480)  # width, height
VALUE_ANY = "--Any--"


class Dropdown(ttk.Combobox):
    def __init__(self, master, values, *args, interactive=True, **kwargs):
        state = "readonly" if not interactive else None
        width = max(len(str(v)) for v in values) + 1
        super().__init__(
            master, *args, state=state, values=values, width=width, **kwargs
        )
        self.set(values[0])


class MultiSelector(ttk.Treeview):
    """
    Widget to select/deselect multiple element in a list, with a scrollbar
    """

    def __init__(self, values, master, *args, height=5, **kwargs):
        self.frame_ = ttk.Frame(master=master)
        super().__init__(
            *args,
            master=self.frame_,
            show="",
            columns=["value"],
            height=min(len(values), height),
            **kwargs
        )
        self.bind("<1>", self.on_click)
        for value in values:
            self.insert("", "end", values=(value,))
        self.column("#1", minwidth=8 * max(len(v) for v in values))
        self.button_frame = ttk.Frame(master=self.frame_)
        self.button_all = ttk.Button(
            master=self.button_frame, text="All", command=self.select_all
        )
        self.button_clear = ttk.Button(
            master=self.button_frame, text="Clear", command=self.select_clear
        )
        self.button_toggle = ttk.Button(
            master=self.button_frame, text="Toggle", command=self.select_toggle
        )
        self.button_frame.pack(side="bottom")
        self.button_all.pack(side="left")
        self.button_clear.pack(side="left")
        self.button_toggle.pack(side="left")
        if height < len(values):
            self.scrollbar_ = ttk.Scrollbar(
                master=self.frame_, orient=tk.VERTICAL, command=self.yview
            )
            self.configure(yscrollcommand=self.scrollbar_.set)
            self.scrollbar_.pack(side="right", expand=True, fill="y")
        self.pack(side="left", expand=True, fill="both")
        self.pack = self.frame_.pack
        self.grid = self.frame_.grid

    def get_selection(self):
        """
        Returns the selected element from the `values` passed to `__init__()`
        """
        return [self.item(item)["values"][0] for item in self.selection()]

    def on_click(self, event):
        """
        Toggle the selection of an item that is clicked on instead of
        the default behavior that is to select only that item
        """
        item = self.identify("item", event.x, event.y)
        if item:
            if item in self.selection():
                self.selection_remove(item)
            else:
                self.selection_add(item)
            return "break"

    def select_all(self):
        """
        Select all items
        """
        self.selection_add(*self.get_children())

    def select_clear(self):
        """
        Deselect all items
        """
        self.selection_remove(*self.get_children())

    def select_toggle(self):
        """
        Toggle the selection of all items
        """
        self.selection_toggle(*self.get_children())


class TkSearchButton(common.AbstractKwargsProvider, ttk.Frame):
    def __init__(self, master):
        super().__init__(master=master)
        self.button = ttk.Button(master=self, text="Search")
        self.mode_label = ttk.Label(master=self, text="criteria to fulfill: ")
        self.mode_selector = Dropdown(
            master=self, values=("All", "Any"), interactive=False
        )
        self.button.pack(side="left")
        self.mode_label.pack(side="left")
        self.mode_selector.pack(side="left")

    def get_kwargs(self):
        return {"operator": self.mode_selector.get()}


class TkFieldGui(common.AbstractKwargsProvider, ttk.Frame):
    """
    Base class for GUI for a single field
    """

    CLASSES = {}
    GUI_DATA_CLS = None

    def __init_subclass__(cls, **kwargs):
        """
        Register subclasses into the CLASSES attribute with key cls.GUI_DATA_CLS
        """
        super().__init_subclass__(**kwargs)
        cls.CLASSES[cls.GUI_DATA_CLS] = cls

    def __init__(self, master, gui_data: parsing.GuiDataBase, field: jsondb.FieldBase):
        super().__init__(master)
        self.gui_data = gui_data
        self.field = field
        self.label = ttk.Label(master=self, text=gui_data.name)
        self.config_frame = ttk.Frame(self)
        self.accept_na_var = tk.BooleanVar(self.config_frame, value=True)
        self.accept_na_button = ttk.Checkbutton(
            master=self.config_frame,
            text="accept N/A",
            onvalue=True,
            offvalue=False,
            variable=self.accept_na_var,
        )
        self.accept_na_var.set(True)

    def pack_configs(self, widgets_groups):
        """
        Packs from left to right the option widgets, adding separator between groups
        (typically lable+button or label+selector)

        widgets_groups: an iterable of iterable of widgets
        """
        previous = False
        for group in widgets_groups:
            if previous:
                ttk.Separator(self.config_frame, orient=tk.VERTICAL).pack(
                    side="left", fill="y", expand=True
                )
            for widget in group:
                widget.pack(side="left")
            previous = True

    @classmethod
    def make(cls, master, gui_data: parsing.GuiDataBase, field: jsondb.FieldBase):
        class_ = cls.CLASSES[type(gui_data)]
        return class_(master=master, gui_data=gui_data, field=field)


class TkOptionGui(TkFieldGui):
    """
    Class for the GUI of Option field
    """

    GUI_DATA_CLS = parsing.OptionGuiData

    def __init__(
        self, master, gui_data: parsing.OptionGuiData, field: jsondb.OptionField
    ):
        super().__init__(master, gui_data, field)
        self.label.pack(side="top", fill="x")
        self.pack_configs([[self.accept_na_button]])
        self.config_frame.pack(side="top")
        if gui_data.multi_selection:
            self.selector = MultiSelector(
                values=gui_data.field_spec["values"], master=self, height=5
            )
        else:
            values = gui_data.field_spec["values"].copy()
            if field.optional:
                values = [VALUE_ANY] + values
            self.selector = Dropdown(master=self, values=values, interactive=False)
        self.selector.pack(side="top")

    def get_kwargs(self):
        args = {
            "accept_missing": self.accept_na_var.get(),
            "operator": self.gui_data.operator,
        }
        if self.gui_data.multi_selection:
            args["valid_values"] = jsondb.ValueSet(self.selector.get_selection())
        else:
            args["valid_values"] = self.selector.get()
        if not args["valid_values"] or args["valid_values"] == VALUE_ANY:
            return None
        return args


class TkIntegerGui(TkFieldGui):
    """
    Class for the GUI of an Integer field
    """

    GUI_DATA_CLS = parsing.IntegerGuiData

    def __init__(
        self, master, gui_data: parsing.IntegerGuiData, field: jsondb.IntegerField
    ):
        super().__init__(master, gui_data, field)
        self.label.pack(side="top", fill="x")
        self.pack_configs([[self.accept_na_button]])
        self.config_frame.pack(side="top")
        values = list(gui_data.listed)
        if field.optional:
            values = [VALUE_ANY] + values
        self.selector = Dropdown(master=self, values=values)
        if field.optional:
            self.selector.set(VALUE_ANY)
        else:
            self.selector.set(field.min_ or field.max_ or 0)
        self.selector.pack(side="top")

    def get_kwargs(self):
        value = self.selector.get()
        if value == VALUE_ANY:
            return None
        value = self.field.bounded_value(int(float(value)))
        self.selector.set(value)
        return {
            "accept_missing": self.accept_na_var.get(),
            "value": value,
            "comparison": self.gui_data.comparison,
        }


class TkTextGui(TkFieldGui):
    GUI_DATA_CLS = parsing.TextGuiData

    def __init__(self, master, gui_data: parsing.TextGuiData, field: jsondb.TextField):
        super().__init__(master, gui_data, field)
        self.mode_label = ttk.Label(master=self.config_frame, text="required lines:")
        self.mode_selector = Dropdown(
            master=self.config_frame, values=("Any", "All"), interactive=False,
        )
        self.selector = tk.Text(master=self, wrap="word", height=5, width=30)
        self.label.pack(side="top", fill="x")
        self.pack_configs(
            [[self.accept_na_button], [self.mode_label, self.mode_selector]]
        )
        self.config_frame.pack(side="top")
        self.selector.pack(side="top")

    def get_kwargs(self):
        text = self.selector.get("1.0", "end-1c")
        values = [line for line in text.split("\n") if line]
        if not values:
            return None
        return {
            "accept_missing": self.accept_na_var.get(),
            "operator": self.mode_selector.get(),
            "value": values,
        }


# FieldTkGui.CLASSES[parsing.TextGuiData] = TextTkGui


class TkHTMLDisplay(common.AbstractHTMLDisplay, tk_html.HTMLScrolledText):
    def display_html(self, html):
        self.set_html(html, strip=False)


class TkSearchCallback(common.AbstractSearchCallback):
    LOGGER = LOGGER

    def show_error(self, title="", message=""):
        tk.messagebox.showerror(title=title, message=message)


class TkNotebook(common.AbstractNotebook, ttk.Notebook):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_tab(self, tab, title=""):
        self.tabs_.append(tab)
        self.add(tab.frame, text=title)


class MainApp(common.AbstractMainApp, tk.Tk):
    PACK_SIDES = ("top", "left")
    FILL = ("x", "y")

    def __init__(self):
        super().__init__()
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.menu = tk.Menu(self)
        self.menu.add_command(label="Open file", command=self.open_file)
        self.config(menu=self.menu)

        self.notebook = TkNotebook(self)
        self.notebook.grid(column=0, row=0, sticky="nsew")

    def set_title(self, title):
        self.title(title)

    def show_error(self, title="", message=""):
        tk.messagebox.showerror(title=title, message=message)

    def ask_file(self):
        path = tk.filedialog.askopenfilename(
            initialdir=self.open_dir_cache,
            title="Open file",
            filetypes=(("JSON files", "*.json"), ("all files", "*.*")),
        )
        return path or None

    def new_tab(self, parsed_file: parsing.ParsedFile):
        """
        Create a new tab
        """
        tab = DotMap()
        # Main frame
        tab.frame = ttk.Frame(self.notebook)
        # Search Area and Result Area
        tab.search = ttk.Frame(tab.frame)
        tab.result = ttk.Frame(tab.frame)
        tab.search.pack(side="left", expand=True, fill="y")
        tab.result.pack(side="right", expand=True, fill="both")
        # Result Area Content
        tab.display = TkHTMLDisplay(master=tab.result, wrap="word", state="disabled",)
        tab.display.pack(side="left", expand=True, fill="both")
        # Search Area content
        ## Search Button
        tab.search_button_gui = TkSearchButton(tab.search)
        tab.search_button_gui.pack(side="top")
        ## Search Fields
        tab.gui_dict = self.make_guis(parsed_file, tab.search)
        tab.search_button_gui.button.configure(
            command=TkSearchCallback(
                parsed_file=parsed_file,
                search_button=tab.search_button_gui,
                gui_dict=tab.gui_dict,
                display=tab.display,
            )
        )
        return tab

    def make_guis(self, parsed_file: parsing.ParsedFile, search_frame: ttk.Frame):
        return self.make_nested_guis(
            parsed_file=parsed_file,
            gui_dict={},
            master_frame=search_frame,
            side_id=0,
            nested_geometry=parsed_file.gui_geometry,
        )

    def make_nested_guis(
        self,
        parsed_file: parsing.ParsedFile,
        gui_dict,
        master_frame,
        side_id,
        nested_geometry,
    ):
        for element in nested_geometry:
            if isinstance(element, list):
                sub_frame = ttk.Frame(master=master_frame)
                self.make_nested_guis(
                    parsed_file=parsed_file,
                    gui_dict=gui_dict,
                    master_frame=sub_frame,
                    side_id=side_id + 1 % 2,
                    nested_geometry=element,
                )
                sub_frame.pack(
                    side=self.PACK_SIDES[side_id], expand=True, fill=self.FILL[side_id]
                )
            else:
                gui = TkFieldGui.make(
                    master=master_frame,
                    gui_data=parsed_file.gui_datas[element],
                    field=parsed_file.database.fields[element],
                )
                gui.pack(
                    side=self.PACK_SIDES[side_id], expand=True, fill=self.FILL[side_id]
                )
                gui_dict[element] = gui
        return gui_dict

    def start(self):
        self.geometry(
            "%dx%d+%d+%d"
            % (
                DEFAULT_SIZE[0],
                DEFAULT_SIZE[1],
                self.winfo_screenwidth() // 2 - DEFAULT_SIZE[0] // 2,
                self.winfo_screenheight() // 2 - DEFAULT_SIZE[1] // 2,
            )
        )
        self.mainloop()
