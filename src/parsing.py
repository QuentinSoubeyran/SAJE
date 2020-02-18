#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module for file parsing utilities of the SAJE project
"""
# Built-in modules
from collections import namedtuple

# Local modules
from . import version
from .json_utils import jsonplus as json
from .json_utils import jsondb

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = version.__version__
__maintainer__ = "Quentin Soubeyran"
__status__ = version.__status__

CACHE_KEY = "__CACHED_DISPLAY_STRING__"

ParsedFile = namedtuple(
    "ParsedFile", ["database", "display_string", "gui_geometry", "gui_datas"]
)


def parse_file(json_file):
    """
    Parses a JSON file that was just loaded, and return a ParsedFile object, ready for
    use to create a GUI and search the data
    """
    field_dict, field_geometry = parse_nested_fields(
        field_dict={}, field_geometry=[], field_nested_list=json_file["fields"]
    )
    display_string = json_file.get("display_string")
    if display_string and json.Type(display_string) is json.Array:
        display_string = "".join(display_string)
    fields = {name: gui_data.field_spec for name, gui_data in field_dict.items()}
    return ParsedFile(
        database=jsondb.Database.from_json(
            {"fields": fields, "data": json_file["data"]}
        ),
        display_string=display_string,
        gui_geometry=field_geometry,
        gui_datas=field_dict,
    )


def get_display(display_string, json_obj):
    if CACHE_KEY not in json_obj:
        if display_string is not None:
            json_obj[CACHE_KEY] = display_string.format(
                **{".".join(key): value for key, value in json.flatten(json_obj)}
            )
        else:
            json_obj[CACHE_KEY] = json.dumps(json_obj, indent=2)
    return json_obj[CACHE_KEY]


class GuiDataBase:
    """
    Base class for parsing JSON data. Separates the Field JSON specification from the data
    aimed at the GUI
    """

    CLASSES = {}

    def __init__(self, json_obj):
        self.name = json_obj.pop("name")

    @staticmethod
    def parse_json(json_obj):
        """
        Main method to parse json data for a field and additional data for the GUI
        """
        type_ = json_obj["type"]
        return GuiDataBase.CLASSES[type_](json_obj)


class OptionGuiData(GuiDataBase):
    """
    Parses the json obejct and stores the Field object and GUI data for an Option field
    """

    def __init__(self, json_obj):
        super().__init__(json_obj)
        self.multi_selection = json_obj.pop("multi_selection", False)
        self.operator = json_obj.pop("operator", "or")
        self.field_spec = json_obj


GuiDataBase.CLASSES[jsondb.OptionField.TYPE] = OptionGuiData


class IntegerGuiData(GuiDataBase):
    """
    Parses the json and stores the Field object and GUI data for an Integer field
    """

    def __init__(self, json_obj):
        super().__init__(json_obj)
        self.listed = json_obj.pop("listed", [])
        self.comparison = json_obj.pop("comparison", "eq")
        self.field_spec = json_obj


GuiDataBase.CLASSES[jsondb.IntegerField.TYPE] = IntegerGuiData


class TextGuiData(GuiDataBase):
    """
    Parsed the json and stores the Field object and GUI data for a Text field
    """

    def __init__(self, json_obj):
        super().__init__(json_obj)
        self.field_spec = json_obj


GuiDataBase.CLASSES[jsondb.TextField.TYPE] = TextGuiData


def parse_nested_fields(field_dict, field_geometry, field_nested_list):
    """
    Recursively parses the nested list of JSON field specification

    Modifies in-place field_dict and field_geometry.
    field_dict is a mapping from field names to GuiDataBase subclasses objects
    field_geometry is a nested list of string, the field names, that specifies the
        layout of the GUI - it essencially mirrors the JSON spec
    """
    for element in field_nested_list:
        if json.Type(element) is json.Array:
            _, nested_geometry = parse_nested_fields(
                field_dict=field_dict, field_geometry=[], field_nested_list=element
            )
            field_geometry.append(nested_geometry)
        elif json.Type(element) is json.Object:
            gui_data = GuiDataBase.parse_json(element)
            if gui_data.name in field_dict:
                raise ValueError("Duplicated field name %s" % gui_data.name)
            field_geometry.append(gui_data.name)
            field_dict[gui_data.name] = gui_data
    return field_dict, field_geometry
