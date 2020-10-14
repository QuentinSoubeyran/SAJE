#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tkinter backend for SAJE project
"""
import functools
import logging
import math
import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox
import tkinter.ttk as ttk
from typing import Literal, Union

import tk_html_widgets as tk_html
from dotmap import DotMap

from .. import parsing, version
from ..backends import common
from ..json_utils import jsondb
from ..json_utils import jsonplus as json

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = version.__version__
__maintainer__ = "Quentin Soubeyran"
__status__ = version.__status__

LOGGER = logging.getLogger("SAJE.backend.tkinter")
DEFAULT_SIZE = (1024, 768)  # width, height
VALUE_ANY = "--Any--"

GeometryType = list[Union["GeometryType", str]]


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


class MultiSelector(ttk.Frame):
    """
    Widget to select/deselect multiple element in a list, with a scrollbar
    """

    class MultiSelectorTree(ttk.Treeview):
        def __init__(self, master, values, *args, height=5, min_height=3, **kwargs):
            super().__init__(
                *args,
                master=master,
                show="tree",
                columns=[],
                height=max(3, min(len(values), height)),
                **kwargs
            )
            self.height_arg = height
            self.min_height_arg = min_height
            self.bind("<1>", self.on_click)

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

    def __init__(
        self,
        master,
        values,
        *args,
        height=5,
        min_height=3,
        cls=MultiSelectorTree,
        **kwargs
    ):
        super().__init__(master=master)
        self.tree = cls(
            *args,
            master=self,
            values=values,
            height=max(3, min(len(values), height)),
            **kwargs
        )
        self.id_value_map = {}
        self.set_values(values)
        # Under buttons
        self.button_all = ttk.Button(master=self, text="All", command=self.select_all)
        self.button_clear = ttk.Button(
            master=self, text="Clear", command=self.select_clear
        )
        self.button_toggle = ttk.Button(
            master=self, text="Toggle", command=self.select_toggle
        )
        self.scrollbar_ = ttk.Scrollbar(
            master=self, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=self.scrollbar_.set)
        self.button_all.grid(row=1, column=0, sticky="ew")
        self.button_clear.grid(row=1, column=1, sticky="ew")
        self.button_toggle.grid(row=1, column=2, sticky="ew")
        self.scrollbar_.grid(row=0, rowspan=2, column=3, sticky="ns")
        self.tree.grid(row=0, column=0, columnspan=3, sticky="nesw")
        self.rowconfigure(0, weight=1)
        for i in range(0, 3):
            self.columnconfigure(i, weight=1)

    def adapt_display(self, item_number):
        height = max(self.tree.min_height_arg, min(item_number, self.tree.height_arg))
        self.tree.config(height=height)

    def set_values(self, values):
        selection = set(self.get_selection())
        self.select_clear()
        self.tree.delete(*self.tree.get_children())
        self.id_value_map = {
            self.tree.insert("", "end", text=str(value)): value for value in values
        }
        self.set_selection(selection & set(values))
        self.adapt_display(len(values))

    def get_selection(self):
        """
        Returns the selected element from the `values` passed to `__init__()`
        """
        return [
            self.id_value_map[item]
            for item in self.tree.selection()
            if item in self.id_value_map
        ]

    def set_selection(self, values):
        """
        Set the current selection from a subset of 'values' passed to __init__
        """
        self.tree.selection_set(
            [
                item
                for item in self.tree.get_children()
                if self.id_value_map[item] in values
            ]
        )

    def select_all(self):
        """
        Select all items
        """
        self.tree.selection_add(*self.tree.get_children())

    def select_clear(self):
        """
        Deselect all items
        """
        self.tree.selection_remove(*self.tree.get_children())

    def select_toggle(self):
        """
        Toggle the selection of all items
        """
        self.tree.selection_toggle(*self.tree.get_children())


def with_callback(method):
    def wrapped(self, *args, **kwargs):
        reactivate = self._active_
        self._active_ = False
        ret = method(self, *args, **kwargs)
        if reactivate:
            self._callback_()
            self._active_ = True
        return ret

    return wrapped


class CallbackMultiSelector(MultiSelector):
    class CallbackMultiSelectorTree(MultiSelector.MultiSelectorTree):
        @with_callback
        def on_click(self, event):
            return super().on_click(event)

    def __init__(self, *args, callback=None, **kwargs):
        self._active_ = False
        super().__init__(
            *args, cls=CallbackMultiSelector.CallbackMultiSelectorTree, **kwargs
        )
        self.tree._active_ = True
        self.tree._callback_ = callback
        self._active_ = True
        self._callback_ = callback

    @with_callback
    def set_values(self, values):
        super().set_values(values)

    @with_callback
    def set_selection(self, values):
        super().set_selection(values)

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
            self.label.grid(row=0, column=0)
            self.dropdown.grid(row=0, column=1)
        elif type_ is json.Value:
            self.single = json_value
        else:
            raise json.JsonTypeError("Invalid type %s for field option" % type_)

    def get(self):
        if self.single is None:
            return self.dropdown.get()
        else:
            return self.single

    def grid(self, *args, **kwargs):
        if self.single is None:
            self.frame.grid(*args, **kwargs)
        else:
            return self.SKIP


class TkSearchButton(common.AbstractKwargsProvider, ttk.Frame):
    def __init__(self, master):
        super().__init__(master=master)
        self.button = ttk.Button(master=self, text="Search")
        self.mode_label = ttk.Label(master=self, text="criteria to fulfill: ")
        self.mode_selector = Dropdown(
            master=self, values=("All", "Any"), interactive=False
        )
        self.status_var = tk.StringVar()
        self.status_var.set("")
        self.status_label = ttk.Label(self, textvariable=self.status_var)
        self.button.grid(row=0, column=0, columnspan=2, stick="ew")
        self.mode_label.grid(row=1, column=0)
        self.mode_selector.grid(row=1, column=1)
        self.status_label.grid(row=2, column=0, columnspan=2)
        for i in range(2):
            self.columnconfigure(i, weight=1)
        for i in range(3):
            self.rowconfigure(i, weight=1)

    def get_kwargs(self):
        return {"operator": self.mode_selector.get()}


class VisibilityMixin(ttk.Widget):
    """
    Class to make a Tk widget handle its visibility more easily
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visible = False

    def grid(self, *args, **kwargs):
        super().grid(*args, **kwargs)
        self.visible = True

    def grid_remove(self, *args, **kwargs):
        super().grid_remove(*args, **kwargs)
        self.visible = False

    def grid_forget(self, *args, **kwargs):
        super().grid_forget(*args, **kwargs)
        self.visible = False

    def set_visible(self):
        if not self.visible:
            self.grid()

    def set_invisible(self):
        if self.visible:
            self.grid_remove()


class TkFieldGui(VisibilityMixin, common.AbstractKwargsProvider, ttk.LabelFrame):
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
        self.visible = True
        self.frame_option = ttk.Frame(self)
        self.var_acceptNA = tk.BooleanVar(self.frame_option, value=True)
        self.button_acceptNA = ttk.Checkbutton(
            master=self.frame_option,
            text="accept N/A",
            onvalue=True,
            offvalue=False,
            variable=self.var_acceptNA,
        )
        self.var_acceptNA.set(True)
        self.var_invert = tk.BooleanVar(self.frame_option, value=False)
        self.button_invert = ttk.Checkbutton(
            master=self.frame_option,
            text="invert",
            onvalue=True,
            offvalue=False,
            variable=self.var_invert,
        )
        self.var_invert.set(False)
        self.frame_option.grid(row=0, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def add_to_grid(self, master, *widgets_groups, row=0, col=0):
        for j, group in enumerate(widgets_groups):
            for i, widget in enumerate(group):
                success = widget.grid(row=row + 2 * j, column=col + 2 * i)
                if success is not OptionalDropdown.SKIP:
                    master.columnconfigure(col + 2 * i, weight=1)
                    if i > 0:
                        sep = ttk.Separator(master, orient=tk.VERTICAL)
                        sep.grid(row=row + 2 * j, column=col + 2 * i - 1)

    def notify_modes(self, modes: set[str]) -> bool:
        if self.gui_data.modes is not None:
            if modes & self.gui_data.modes:
                self.set_visible()
            else:
                self.set_invisible()
        return self.visible

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
        self.ops_selector = OptionalDropdown(
            master=self.frame_option, json_value=gui_data.operator, label="operation"
        )
        if gui_data.multi_selection:
            self.add_to_grid(
                self.frame_option,
                [self.button_acceptNA, self.button_invert, self.ops_selector],
            )
            self.selector = MultiSelector(
                values=gui_data.field_spec["values"], master=self, height=5
            )
            self.selector.select_all()
            self.selector.grid(row=1, column=0, sticky="nesw")
        else:
            self.add_to_grid(
                self.frame_option,
                [self.button_acceptNA, self.button_invert, self.ops_selector],
            )
            values = gui_data.field_spec["values"].copy()
            if field.optional:
                values = [VALUE_ANY] + values
            self.selector = Dropdown(master=self, values=values, interactive=False)
            self.selector.grid(row=1, column=0)
        self.rowconfigure(1, weight=1)

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
        self.comp_selector = OptionalDropdown(
            master=self.frame_option, json_value=gui_data.comparison, label="comparison"
        )
        self.add_to_grid(
            self.frame_option,
            [self.button_acceptNA, self.button_invert, self.comp_selector],
        )
        values = list(gui_data.listed)
        if field.optional:
            values = [VALUE_ANY] + values
        self.selector = Dropdown(master=self, values=values)
        if field.optional:
            self.selector.set(VALUE_ANY)
        else:
            self.selector.set(field.min_ or field.max_ or 0)
        self.selector.grid(row=1, column=0)
        self.rowconfigure(1, weight=1)

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
        self.add_to_grid(self.frame_option, [self.button_acceptNA, self.button_invert])
        self.add_to_grid(
            self.frame_config_selectors, [self.selector_case, self.selector_mode]
        )
        self.selector = tk.Text(master=self, wrap="word", height=5, width=30)
        self.frame_config_selectors.grid(row=1, column=0)
        self.selector.grid(row=2, column=0, sticky="nsew")
        for i in range(1, 3):
            self.rowconfigure(i, weight=1)

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


class VisibleSeparator(VisibilityMixin, ttk.Separator):
    pass


class TkNestedGui(VisibilityMixin, ttk.Frame):
    """
    Class for the nested GUI of search fields
    """

    def __init__(
        self,
        master,
        parsed_file: parsing.ParsedFile,
        nested_geometry: GeometryType,
        axis: Literal["x", "y"],
    ):
        super().__init__(master)
        self.nested_guis = []
        self.separators = []
        # Configure self on the axis
        if axis == "x":
            self.rowconfigure(0, weight=1)
        else:
            self.columnconfigure(0, weight=1)
        # Analyze nested geometry
        configure = self.columnconfigure if axis == "x" else self.rowconfigure
        for i, element in enumerate(nested_geometry):
            if isinstance(element, list):
                new_gui = TkNestedGui(
                    master=self,
                    parsed_file=parsed_file,
                    nested_geometry=element,
                    axis="x" if axis == "y" else "y",
                )
            else:
                new_gui = TkFieldGui.make(
                    master=self,
                    gui_data=parsed_file.gui_datas[element],
                    field=parsed_file.database.fields[element],
                )
            # Add the new gui element (frame or actual Gui)
            # to the grid
            self.nested_guis.append(new_gui)
            new_gui.grid(
                row=0 if axis == "x" else 2 * i,
                column=0 if axis == "y" else 2 * i,
                sticky="nsew",
            )
            configure(2 * i, weight=1)
            if i > 0:
                sep = VisibleSeparator(
                    self, orient=tk.HORIZONTAL if axis == "y" else tk.VERTICAL
                )
                sep.grid(
                    row=0 if axis == "x" else 2 * i - 1,
                    column=0 if axis == "y" else 2 * i - 1,
                    sticky="ns" if axis == "x" else "ew",
                )
                new_gui.preceding_separator = sep
                self.separators.append(sep)

    def get_flat_gui_dict(self) -> dict[str, TkFieldGui]:
        d = {
            tk_field.gui_data.name: tk_field
            for tk_field in self.nested_guis
            if not isinstance(tk_field, TkNestedGui)
        }
        for inner in [ng for ng in self.nested_guis if isinstance(ng, TkNestedGui)]:
            d |= inner.get_flat_gui_dict()
        return d

    def notify_modes(self, modes: set[str]) -> bool:
        # dict respects insertion ordering
        any_visible = False
        for gui in self.nested_guis:
            res = gui.notify_modes(modes)
            if hasattr(gui, "preceding_separator"):
                if res:
                    gui.preceding_separator.set_visible()
                else:
                    gui.preceding_separator.set_invisible()
            any_visible = any_visible or res
        if any_visible:
            self.set_visible()
        else:
            self.set_invisible()
        return any_visible


class TkHTMLDisplay(common.AbstractHTMLDisplay, tk_html.HTMLScrolledText):
    def display_html(self, html):
        self.set_html(html, strip=False)


class TkSearchCallback(common.AbstractSearchCallback):
    LOGGER = LOGGER

    def __init__(self, *args, textvar=None, app=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.textvar = textvar
        self.app = app

    def show_error(self, title="", message=""):
        tk.messagebox.showerror(title=title, message=message)

    def set_status(self, msg):
        if self.textvar is not None:
            self.textvar.set("Status: " + msg)
            if self.app is not None:
                self.app.update()


class TkNotebook(common.AbstractNotebook, ttk.Notebook):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_tab(self, tab, title=""):
        self.tabs_.append(tab)
        self.add(tab.frame_main, text=title)
        tab.frame_main.add(tab.frame_search)
        tab.frame_main.add(tab.display)


class MainApp(common.AbstractMainApp, tk.Tk):
    PACK_SIDES = ("top", "left")
    FILL = ("x", "y")
    ORIENT = (tk.HORIZONTAL, tk.VERTICAL)

    def __init__(self):
        super().__init__()
        s = ttk.Style()
        if "clam" in s.theme_names():
            s.theme_use("clam")
            s.configure("Sash", gripcount=25)
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
        tab = DotMap(_dynamic=False)
        # Main frame
        tab.frame_main = ttk.PanedWindow(self.notebook, orient=tk.HORIZONTAL)
        tab.frame_main.rowconfigure(0, weight=1)
        for i in range(2):
            tab.frame_main.columnconfigure(i, weight=1)
        # Search Area
        tab.frame_search = ttk.Frame(tab.frame_main)
        tab.frame_search.columnconfigure(0, weight=1)
        for i in range(2):
            tab.frame_search.rowconfigure(i, weight=1)
        ## Upper frame
        tab.frame_search_upper = ttk.Frame(tab.frame_search)
        tab.frame_search_upper.rowconfigure(0, weight=1)
        for i in range(2):
            tab.frame_search_upper.columnconfigure(i, weight=1)
        tab.frame_search_upper.grid(row=0, column=0, sticky="nsew")
        ### Mode selector (if any)
        tab.gui_dict = {}
        tab.modes_selector = None
        if len(parsed_file.modes) > 1:
            tab.frame_mode = ttk.LabelFrame(
                tab.frame_search_upper, text="Select active modes"
            )
            tab.modes_selector = CallbackMultiSelector(
                master=tab.frame_mode,
                values=parsed_file.modes,
                callback=functools.partial(self.on_modes, tab),
            )
            tab.modes_selector._active_ = False
            tab.modes_selector.select_all()
            tab.modes_selector._active_ = True
            tab.modes_selector.grid(row=0, column=0, sticky="nsew")
            tab.frame_mode.rowconfigure(0, weight=1)
            tab.frame_mode.columnconfigure(0, weight=1)
            tab.frame_mode.grid(row=0, column=0, sticky="nsew")
        ### Search Button
        tab.search_button = TkSearchButton(tab.frame_search_upper)
        tab.search_button.grid(row=0, column=1, sticky="nsew")

        ## Search Fields
        tab.nested_search_fields = TkNestedGui(
            master=tab.frame_search,
            parsed_file=parsed_file,
            nested_geometry=parsed_file.gui_geometry,
            axis="y",
        )
        tab.nested_search_fields.grid(row=1, column=0, sticky="nsew")
        tab.gui_dict = tab.nested_search_fields.get_flat_gui_dict()

        # Result Area
        tab.display = TkHTMLDisplay(
            master=tab.frame_main, wrap="word", state="disabled", width=-10
        )
        tab.search_button.button.configure(
            command=TkSearchCallback(
                parsed_file=parsed_file,
                search_button=tab.search_button,
                gui_dict=tab.gui_dict,
                display=tab.display,
                modes_getter=tab.modes_selector.get_selection
                if tab.modes_selector
                else lambda: None,
                textvar=tab.search_button.status_var,
                app=self,
            )
        )
        return tab

    def on_modes(self, tab):
        modes = set(tab.modes_selector.get_selection())
        tab.nested_search_fields.notify_modes(modes)

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
