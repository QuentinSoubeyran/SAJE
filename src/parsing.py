#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module for file parsing utilities of the SAJE project
"""
# Built-in modules
from collections import namedtuple
from abc import ABC, abstractmethod

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
    "ParsedFile", ["name", "display_string", "gui_geometry", "gui_datas", "database"]
)


class DisplayString(ABC):
    """
    Class for handling display string format
    """

    CLASSES = []
    KEYWORDS = None

    def __init_subclass__(cls, **kwargs):
        """
        Register subclasses into the CLASSES attribute, under the key subclass.TYPE
        """
        super().__init_subclass__(**kwargs)
        if cls.KEYWORDS is not None:
            cls.CLASSES.append((cls.KEYWORDS, cls))

    @classmethod
    def from_json(cls, json_obj):
        if json_obj is None:
            return DefaultDS()
        type_ = json.Type(json_obj)
        if type_ is json.Value:
            return StringDS(json_obj)
        elif type_ is json.Array:
            return ArrayDS(json_obj)
        elif type_ is json.Object:
            json_kw = set(json_obj)
            for keywords, class_ in cls.CLASSES:
                if keywords & json_kw == keywords:
                    return class_(json_obj)
            raise ValueError(
                "No display_string object matches the keywords %s" % json_kw
            )

    @abstractmethod
    def format(self, json_obj):
        """
        Returns the display string for the passed json object
        """


class DefaultDS(DisplayString):
    def format(self, json_obj):
        return json.dumps(json_obj, indent=2)


class StringDS(DisplayString):
    """
    Handles formating a final string
    """

    def __init__(self, string):
        self.string = str(string)

    def format(self, json_obj):
        type_ = json.Type(json_obj)
        if type_ is json.Object:
            return self.string.format(
                **{
                    ".".join(str(k) for k in key): value
                    for (key, value) in json.flatten(json_obj)
                }
            )
        elif type_ is json.Array:
            return self.string.format(json_obj)
        else:
            return self.string.format(value=json_obj)


class ArrayDS(DisplayString):
    """
    Handles concatenating a json-array of display strings
    """

    def __init__(self, json_obj):
        self.display_strings = [self.from_json(sub_json) for sub_json in json_obj]

    def format(self, json_obj):
        return "".join(ds.format(json_obj) for ds in self.display_strings)


class TableDS(DisplayString):
    """
    Handles switching based on the value of a key
    Empty string is used as a default route
    """

    KEYWORDS = {"key", "table"}

    def __init__(self, json_obj):
        self.key = json_obj["key"]
        self.table = {
            key: self.from_json(display_string)
            for key, display_string in json_obj["table"].items()
        }
        if "" not in self.table:
            raise ValueError(
                "table display_string requires a default under the empty key"
            )

    def format(self, json_obj):
        if json.has(json_obj, self.key):
            value = json.get(json_obj, self.key)
            if value in self.table:
                return self.table[value].format(json_obj)
        return self.table[""].format(json_obj)


class ForallDS(DisplayString):
    """
    Handles a for loop on sub-items
    """

    KEYWORDS = {"forall", "display_string"}

    def __init__(self, json_obj):
        self.key = json_obj["forall"]
        self.display_string = self.from_json(json_obj["display_string"])
        self.sep = json_obj.get("separator", "")

    def format(self, json_obj):
        if json.has(json_obj, self.key):
            return self.sep.join(
                self.display_string.format(sub_json)
                for sub_json in json.get(json_obj, self.key)
            )
        return ""


def parse_file(json_file, filename):
    """
    Parses a JSON file that was just loaded, and return a ParsedFile object, ready for
    use to create a GUI and search the data
    """
    json_version = json_file.get("version", None)
    if json_version is None:
        raise ValueError("File %s has no version" % filename)
    prog_ver = version.__version__.split(".")
    json_ver = json_version.split(".")
    if prog_ver[0] != json_ver[0] or prog_ver[1] < json_ver[1]:
        raise ValueError(
            "SAJE version %s cannot load format from version %s"
            % (version.__version__, json_version)
        )
    field_dict, field_geometry = parse_nested_fields(
        field_dict={}, field_geometry=[], field_nested_list=json_file["fields"]
    )
    fields = {name: gui_data.field_spec for name, gui_data in field_dict.items()}
    return ParsedFile(
        name=json_file.get("name", filename),
        display_string=DisplayString.from_json(json_file.get("display_string")),
        gui_geometry=field_geometry,
        gui_datas=field_dict,
        database=jsondb.Database.from_json(
            {"fields": fields, "data": json_file["data"]}
        ),
    )


def get_display(display_string, json_obj):
    if CACHE_KEY not in json_obj:
        json_obj[CACHE_KEY] = display_string.format(json_obj)
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
