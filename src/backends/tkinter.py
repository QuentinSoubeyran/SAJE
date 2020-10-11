#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tkinter backend for SAJE project
"""
# Built-in modules
import functools
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
from ..json_utils import jsonplus as json
from .. import parsing
from ..backends import common

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = version.__version__
__maintainer__ = "Quentin Soubeyran"
__status__ = version.__status__

LOGGER = logging.getLogger("SAJE.backend.tkinter")
DEFAULT_SIZE = (1024, 768)  # width, height
VALUE_ANY = "--Any--"


class Dropdown(ttk.Combobox):
    def __init__(self, master, values, *args, interactive=True, **kwargs):
        state = "readonly" if not interactive else None
        width = max(len(str(v)) for v in values) + 1
        values = list(values)
        super().__init__(
            master, *args, state=state, values=values, width=width, **kwargs
        )
        if values:
            self.set(values[0])

    def set_values(self, values):
        selected = self.get()
        values = list(values)
        self.configure(values=values, width=max(len(str(v)) for v in values) + 1)
        self.set(selected if selected in values else values[0])


class MultiSelector(ttk.Treeview):
    """
    Widget to select/deselect multiple element in a list, with a scrollbar
    """

    def __init__(self, master, values, *args, height=5, min_height=3, **kwargs):
        self.frame_ = ttk.Frame(master=master)
        super().__init__(
            *args,
            master=self.frame_,
            show="tree",
            columns=[],
            height=max(3, min(len(values), height)),
            **kwargs
        )
        self.height_arg = height
        self.min_height_arg = min_height
        # self.column("cache", width=0, minwidth=0, stretch=False)
        self.bind("<1>", self.on_click)
        # Under buttons
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
        self.button_frame.pack(side="bottom", fill="x")
        self.button_all.pack(side="left", fill="x", expand=True)
        self.button_clear.pack(side="left", fill="x", expand=True)
        self.button_toggle.pack(side="left", fill="x", expand=True)
        self.scrollbar_ = ttk.Scrollbar(
            master=self.frame_, orient=tk.VERTICAL, command=self.yview
        )
        self.configure(yscrollcommand=self.scrollbar_.set)
        self.scrollbar_.pack(side="right", expand=False, fill="y")
        self.pack(side="left", expand=True, fill="both")
        self.id_value_map = {}
        self.set_values(values)
        self.pack = self.frame_.pack
        self.grid = self.frame_.grid

    def adapt_display(self, item_number):
        height = max(self.min_height_arg, min(item_number, self.height_arg))
        self.config(height=height)

    def set_values(self, values):
        selection = set(self.get_selection())
        self.select_clear()
        self.delete(*self.get_children())
        self.id_value_map = {
            self.insert("", "end", text=str(value)): value for value in values
        }
        self.set_selection(selection & set(values))
        self.adapt_display(len(values))

    def get_selection(self):
        """
        Returns the selected element from the `values` passed to `__init__()`
        """
        return [
            self.id_value_map[item]
            for item in self.selection()
            if item in self.id_value_map
        ]

    def set_selection(self, values):
        """
        Set the current selection from a subset of 'values' passed to __init__
        """
        self.selection_set(
            [item for item in self.get_children() if self.id_value_map[item] in values]
        )

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


class CallbackMultiSelector(MultiSelector):
    def __init__(self, *args, callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._callback_ = callback
        self._active_ = True
    
    @staticmethod
    def with_callback(method):
        def wrapped(self, *args, **kwargs):
            reactivate = self._active_
            self._active_ = False
            method(self, *args, **kwargs)
            if reactivate:
                self._callback_()
                self._active_ = True
        return wrapped

    @with_callback
    def set_values(self, values):
        super().set_values(values)
    
    @with_callback
    def set_selection(self, values):
        super().set_selection(values)
    
    @with_callback
    def selection_remove(self, *args, **kwargs):
        super().selection_remove(*args, **kwargs)
    
    @with_callback
    def selection_add(self, *args, **kwargs):
        super().selection_add(*args, **kwargs)
    
    @with_callback
    def selection_toggle(self, *args, **kwargs):
        super().selection_toggle(*args, **kwargs)
    
    @with_callback    
    def select_all(self):
        super().select_all()

    @with_callback
    def select_clear(self):
        super().select_clear()

    @with_callback
    def select_toggle(self):
        super().select_toggle()

class OptionalDropdown:
    """
    If a single value is passed, just returns the value, else has a graphic component
    """

    SKIP = object()

    def __init__(self, master, json_value, label):
        type_ = json.Type(json_value)
        if type_ is json.Array:
            self.single = None
            self.frame = ttk.Frame(master=master)
            self.label = ttk.Label(master=self.frame, text=label)
            self.dropdown = Dropdown(
                master=self.frame, values=json_value, interactive=False
            )
            self.dropdown.set(json_value[0])
            self.label.pack(side="left")
            self.dropdown.pack(side="left")
        elif type_ is json.Value:
            self.single = json_value
        else:
            raise json.JsonTypeError("Invalid type %s for field option" % type_)

    def get(self):
        if self.single is None:
            return self.dropdown.get()
        else:
            return self.single

    def pack(self, *args, **kwargs):
        if self.single is None:
            self.frame.pack(*args, **kwargs)
        else:
            return self.SKIP


class TkSearchButton(common.AbstractKwargsProvider, ttk.Frame):
    def __init__(self, master):
        super().__init__(master=master)
        self.button = ttk.Button(master=self, text="Search")
        self.mode_frame = ttk.Frame(self)
        self.mode_label = ttk.Label(
            master=self.mode_frame, text="criteria to fulfill: "
        )
        self.mode_selector = Dropdown(
            master=self.mode_frame, values=("All", "Any"), interactive=False
        )
        self.button.pack(side="top")
        self.mode_frame.pack(side="top")
        self.mode_label.pack(side="left")
        self.mode_selector.pack(side="left")

    def get_kwargs(self):
        return {"operator": self.mode_selector.get()}


class TkFieldGui(common.AbstractKwargsProvider, ttk.LabelFrame):
    """
    Base class for the GUI of a single search field
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
        super().__init__(master, text=gui_data.name)
        self.gui_data = gui_data
        self.field = field
        self.hidden = True
        # self.label = ttk.Label(master=self, text=gui_data.name)
        self.frame_config = ttk.Frame(self)
        self.var_acceptNA = tk.BooleanVar(self.frame_config, value=True)
        self.button_acceptNA = ttk.Checkbutton(
            master=self.frame_config,
            text="accept N/A",
            onvalue=True,
            offvalue=False,
            variable=self.var_acceptNA,
        )
        self.var_acceptNA.set(True)
        self.var_invert = tk.BooleanVar(self.frame_config, value=False)
        self.button_invert = ttk.Checkbutton(
            master=self.frame_config,
            text="invert",
            onvalue=True,
            offvalue=False,
            variable=self.var_invert,
        )
        self.var_invert.set(False)
    
    def show(self):
        if self.hidden:
            self.frame_config.pack(side="top", fill="x")
            self.hidden = False
    
    def hide(self):
        if not self.hidden:
            self.frame_config.pack_forget()
            self.hidden = True

    def pack_configs(self, widgets_groups, *, master=None):
        """
        Packs from left to right the option widgets, adding separator between groups
        (typically lable+button or label+selector)

        widgets_groups: an iterable of iterable of widgets
        """
        if master is None:
            master = self.frame_config
        previous = False
        last_sep = None
        for group in widgets_groups:
            if previous:
                last_sep = ttk.Separator(master=master, orient=tk.VERTICAL)
                last_sep.pack(side="left", fill="y", expand=True)
            previous = any(
                [
                    widget.pack(side="left", expand=True) is not OptionalDropdown.SKIP
                    for widget in group
                ]
            )
        if last_sep and not previous:
            last_sep.pack_forget()

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
        # self.label.pack(side="top", fill="x", expand=True)
        self.ops_selector = OptionalDropdown(
            master=self.frame_config, json_value=gui_data.operator, label="operation"
        )
        if gui_data.multi_selection:
            self.pack_configs([[self.button_acceptNA], [self.ops_selector]])
            self.selector = MultiSelector(
                values=gui_data.field_spec["values"], master=self, height=5
            )
            self.selector.select_all()
        else:
            self.pack_configs(
                [[self.button_acceptNA], [self.button_invert], [self.ops_selector]]
            )
            values = gui_data.field_spec["values"].copy()
            if field.optional:
                values = [VALUE_ANY] + values
            self.selector = Dropdown(master=self, values=values, interactive=False)
        self.show()
    
    def show(self):
        if self.hidden:
            super().show()
            if self.gui_data.multiselection:
                self.selector.pack(side="top", expand=True, fill="y")
            else:
                self.selector.pack(side="top")
        
    def hide(self):
        if not self.hidden:
            super().hide()
            self.selector.pack_forget()

    def get_kwargs(self):
        args = {
            "invert": self.var_invert.get()
            if not self.gui_data.multi_selection
            else False,
            "accept_missing": self.var_acceptNA.get(),
            "operator": self.ops_selector.get(),
        }
        if self.gui_data.multi_selection:
            args["valid_values"] = jsondb.ValueSet(self.selector.get_selection())
        else:
            args["valid_values"] = self.selector.get()
            if args["valid_values"] == VALUE_ANY:
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
        # self.label.pack(side="top", fill="x", expand=True)
        self.comp_selector = OptionalDropdown(
            master=self.frame_config, json_value=gui_data.comparison, label="comparison"
        )
        self.pack_configs(
            [[self.button_acceptNA], [self.button_invert], [self.comp_selector]]
        )
        self.frame_config.pack(side="top")
        values = list(gui_data.listed)
        if field.optional:
            values = [VALUE_ANY] + values
        self.selector = Dropdown(master=self, values=values)
        if field.optional:
            self.selector.set(VALUE_ANY)
        else:
            self.selector.set(field.min_ or field.max_ or 0)
        self.show()
    
    def show(self):
        if self.hidden:
            super().show()
            self.selector.pack(side="top")
    
    def hide(self):
        if not self.hidden:
            super().hide()
            self.selector.pack_forget()

    def get_kwargs(self):
        value = self.selector.get()
        if value == VALUE_ANY:
            return None
        value = self.field.bounded_value(int(float(value)))
        self.selector.set(value)
        return {
            "accept_missing": self.var_acceptNA.get(),
            "invert": self.var_invert.get(),
            "value": value,
            "comparison": self.comp_selector.get(),
        }


class TkTextGui(TkFieldGui):
    GUI_DATA_CLS = parsing.TextGuiData

    def __init__(self, master, gui_data: parsing.TextGuiData, field: jsondb.TextField):
        super().__init__(master, gui_data, field)
        self.frame_config_selectors = ttk.Frame(self)
        self.selector_case = OptionalDropdown(
            master=self.frame_config_selectors,
            json_value=gui_data.case,
            label="case sensitive:",
        )
        self.selector_mode = OptionalDropdown(
            master=self.frame_config_selectors,
            json_value=gui_data.operator,
            label="required lines:",
        )
        self.selector = tk.Text(master=self, wrap="word", height=5, width=30)
        # self.label.pack(side="top", fill="x", expand=True)
        self.pack_configs([[self.button_acceptNA], [self.button_invert]])
        self.pack_configs(
            [[self.selector_case], [self.selector_mode]],
            master=self.frame_config_selectors,
        )
        self.show()
        
    
    def show(self):
        if self.hidden:
            super().show()
            self.frame_config_selectors.pack(side="top", fill="x")
            self.selector.pack(side="top", expand=True, fill="both")
    
    def hide(self):
        if not self.hidden:
            super().hide()
            self.frame_config_selectors.pack_forget()
            self.selector.pack_forget()

    def get_kwargs(self):
        text = self.selector.get("1.0", "end-1c")
        values = [line for line in text.split("\n") if line]
        if not values:
            return None
        return {
            "accept_missing": self.var_acceptNA.get(),
            "invert": self.var_invert.get(),
            "operator": self.selector_mode.get(),
            "case": eval(self.selector_case.get()),
            "value": values,
        }


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
        tab.frame.add(tab.search)
        tab.frame.add(tab.display)


class MainApp(common.AbstractMainApp, tk.Tk):
    PACK_SIDES = ("top", "left")
    FILL = ("x", "y")
    ORIENT = (tk.HORIZONTAL, tk.VERTICAL)

    def __init__(self):
        super().__init__()
        s = ttk.Style()
        s.configure("Sash", gripcount=10)
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
        tab.frame = ttk.PanedWindow(self.notebook, orient=tk.HORIZONTAL)
        # Search Area and Result Area
        tab.search = ttk.Frame(tab.frame)
        # Search Area content
        ## Search Button
        tab.search_frame = ttk.Frame(tab.search)
        tab.search_button_gui = TkSearchButton(tab.search_frame)
        tab.gui_dict = {}
        if len(parsed_file.modes > 1):
            tab.modes_selector = CallbackMultiSelector(
                master=tab.search_frame,
                values=parsed_file.modes,
                callback=functools.partial(self.on_modes, tab)
            )
            tab.modes_selector.select_all()
            tab.modes_selector.pack(side="left", expand=True, fill="both")
        tab.search_button_gui.pack(side="right", expand=True, fill="both")
        tab.search_frame.pack(side="top", expand=True, fill="both")
        ## Search Fields
        tab.gui_dict = self.make_guis(parsed_file, tab.search)
        # Result Area Content
        tab.display = TkHTMLDisplay(
            master=tab.frame, wrap="word", state="disabled", width=-10
        )
        tab.search_button_gui.button.configure(
            command=TkSearchCallback(
                parsed_file=parsed_file,
                search_button=tab.search_button_gui,
                gui_dict=tab.gui_dict,
                display=tab.display,
            )
        )
        return tab
    
    def on_modes(self, tab):
        modes = set(tab.modes_selector.get_selection())
        for gui in tab.gui_dict.values():
            if gui.gui_data.modes is not None:
                if modes & gui.gui_data.modes:
                    gui.show()
                else:
                    gui.hide()

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
        for i, element in enumerate(nested_geometry):
            if i > 0:
                ttk.Separator(master_frame, orient=self.ORIENT[side_id]).pack(
                    side=self.PACK_SIDES[side_id], expand=True, fill=self.FILL[side_id]
                )
            if isinstance(element, list):
                sub_frame = ttk.Frame(master=master_frame)
                self.make_nested_guis(
                    parsed_file=parsed_file,
                    gui_dict=gui_dict,
                    master_frame=sub_frame,
                    side_id=(side_id + 1) % 2,
                    nested_geometry=element,
                )
                sub_frame.pack(
                    side=self.PACK_SIDES[side_id],
                    expand=True,
                    fill="both",  # self.FILL[side_id]
                )
            else:
                gui = TkFieldGui.make(
                    master=master_frame,
                    gui_data=parsed_file.gui_datas[element],
                    field=parsed_file.database.fields[element],
                )
                gui.pack(
                    side=self.PACK_SIDES[side_id],
                    expand=True,
                    fill="both",  # self.FILL[side_id]
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
