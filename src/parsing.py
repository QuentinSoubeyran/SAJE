#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module for file parsing utilities of the SAJE project
"""
# Built-in modules
from collections import namedtuple
from abc import ABC, abstractmethod
import warnings

# Local modules
from . import version
from .json_utils import jsonplus as json
from .json_utils import jsondb
from .utils import NocaseList, err_str

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = version.__version__
__maintainer__ = "Quentin Soubeyran"
__status__ = version.__status__

CACHE_KEY = "__CACHED_DISPLAY_STRING__"
MISSING = object()
MAYBE = object()

ParsedFile = namedtuple(
    "ParsedFile", ["name", "display_string", "gui_geometry", "gui_datas", "database", "modes"]
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
        obj = None
        if json_obj is None:
            obj = DefaultDS()
        type_ = json.Type(json_obj)
        if type_ is json.Value:
            obj = StringDS(json_obj)
        elif type_ is json.Array:
            obj = ArrayDS(json_obj)
        elif type_ is json.Object:
            json_kw = set(json_obj)
            for keywords, class_ in cls.CLASSES:
                if keywords & json_kw == keywords:
                    obj = class_(json_obj)
                    break
            else:
                raise ValueError(
                    "No display_string object matches the keywords %s" % json_kw
                )
        if obj is None:
            raise ValueError(
                "Cannot parse display string definition:\n%s"
                % json.dumps(json_obj, indent=4)
            )
        obj.definition = json.dumps(json_obj, indent=4)
        return obj

    def format(self, json_obj):
        """
        Returns the display string for the passed json object
        """
        try:
            return self._format(json_obj)
        except Exception as err:
            return (
                f"&lt;&lt;ERROR: {err_str(err)}\n"
                f"JSON VALUE:\n{json.dumps(json_obj, indent=4)}\n"
                f"DISPLAY STRING DEF:\n{getattr(self, 'definition', '--Unknown--')}\n&gt;&gt;"
            )
    
    @abstractmethod
    def _format(self, json_obj):
        """
        the actual format implementation
        """


class DefaultDS(DisplayString):
    def _format(self, json_obj):
        return json.dumps(json_obj, indent=2)


class StringDS(DisplayString):
    """
    Handles formating a final string
    """

    def __init__(self, string):
        self.string = str(string)

    def _format(self, json_obj):
        type_ = json.Type(json_obj)
        if type_ is json.Object:
            return self.string.format(
                **{
                    ".".join(str(k) for k in key): value
                    for (key, value) in json.flatten(json_obj)
                }
            )
        elif type_ is json.Array:
            return self.string.format(*json_obj)
        else:
            return self.string.format(value=json_obj)


class ArrayDS(DisplayString):
    """
    Handles concatenating a json-array of display strings
    """

    def __init__(self, json_obj):
        self.display_strings = [self.from_json(sub_json) for sub_json in json_obj]

    def _format(self, json_obj):
        return "".join(ds.format(json_obj) for ds in self.display_strings)

class IfKeyDS(DisplayString):
    """
    Handles displaying conditional on the presence of a key
    """

    KEYWORDS = {"if_key", "display_string"}

    def __init__(self, json_obj):
        self.key = json_obj["if_key"]
        self.display_string = self.from_json(json_obj["display_string"])
    
    def _format(self, json_obj):
        if json.has(json_obj, self.key):
            return self.display_string.format(json_obj)
        return ""

class JsonTypeDS(DisplayString):
    """
    Handles an if on JSON types
    """

    KEYWORDS = {"if_json_type", "json_value", "json_array", "json_object"}

    def __init__(self, json_obj):
        self.key = json_obj["if_json_type"]
        self.table = {
            key: self.from_json(json_obj[key])
            for key in {"json_value", "json_array", "json_object"}
        }
    
    def _format(self, json_obj):
        if json.has(json_obj, self.key):
            t = json.Type(json.get(json_obj, self.key))
            if t is json.Value:
                return self.table["json_value"].format(json_obj)
            elif t is json.Array:
                return self.table["json_array"].format(json_obj)
            elif t is json.Object:
                return self.table["json_object"].format(json_obj)
        raise KeyError(self.key)

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

    def _format(self, json_obj):
        if json.has(json_obj, self.key):
            value = json.get(json_obj, self.key)
            try:
                if value in self.table:
                    return self.table[value].format(json_obj)
            except Exception as err:
                warnings.warn(
                    f"Encountered {err_str(err)} in Table Display String\n"
                    f"JSON OBJECT:\n{json.dumps(json_obj, indent=4)}"
                    f"DISPLAY STRING DEF:\n{getattr(self, 'definition', '--unknonwn--')}"
                )
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

    def _format(self, json_obj):
        t = json.Type(json_obj)
        if t is json.Array:
            return self.sep.join(
                self.display_string.format(e)
                for e in json_obj
            )
        elif t is json.Object:
            if json.has(json_obj, self.key):
                return self.sep.join(
                    self.display_string.format(sub_json)
                    for sub_json in json.get(json_obj, self.key)
                )
            return ""
        else:
            raise ValueError("ERROR: cannot use forall display string on value")


def get_display(display_string, json_obj):
    if CACHE_KEY not in json_obj:
        json_obj[CACHE_KEY] = display_string.format(json_obj)
    return json_obj[CACHE_KEY]


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
    modes = set.union(gui_data.modes or set() for gui_data in field_dict)
    return ParsedFile(
        name=json_file.get("name", filename),
        display_string=DisplayString.from_json(json_file.get("display_string")),
        gui_geometry=field_geometry,
        gui_datas=field_dict,
        database=jsondb.Database.from_json(
            {"fields": fields, "data": json_file["data"]}
        ),
        modes=modes
    )





class GuiDataBase:
    """
    Base class for parsing JSON data. Separates the Field JSON specification from the data
    aimed at the GUI
    """

    CLASSES = {}
    TYPE = None
    NAME = None
    OPS = NocaseList(name for ops in jsondb.Operator for name in ops.aliases)
    COMP = NocaseList(name for comp in jsondb.Comparison for name in comp.aliases)

    def __init_subclass__(cls, **kwargs):
        """
        Register subclasses into the CLASSES attribute, under the key subclass.TYPE
        """
        super().__init_subclass__(**kwargs)
        if cls.TYPE is not None:
            cls.CLASSES[cls.TYPE] = cls

    def __init__(self, json_obj):
        self.name = self.coerce(json_obj, "name", str)
        self.modes = self.coerce(json_obj, "modes", str, default=None, is_array=MAYBE)
        if isinstance(self.modes, list):
            self.modes = set(self.modes)
        elif isinstance(self.modes, str):
            self.modes = set([self.modes])

    @staticmethod
    def parse_json(json_obj):
        """
        Main method to parse json data for a field and additional data for the GUI
        """
        type_ = json_obj["type"]
        return GuiDataBase.CLASSES[type_](json_obj)

    @classmethod
    def coerce(
        cls, json_obj, key, type_, default=MISSING, is_array=False, valid_values=None
    ):
        """
        Verifies the values from the json are valid, and return them

        Args:
            json_obj    : the json object to extract values from
            key         : the key to extract value from
            type_       : the python type of values. Raises TypeError if the extracted type is wrong
            default     : the default value.  Raise ValueError if default is `MISSING` and the json has not value for the specified key
            is_array   : `False`: value cannot be an array. `MAYBE`: value can be an Array of value. `True`: value must be as Array
            valid_values: the list of valid values, if any
        
        Returns:
            Equivalent to json.pop(key)
        
        Raises:
            TypeError if the type of the value is wrong
            ValueError if the value is not in valid_values
        """
        if key not in json_obj:
            if default is not MISSING:
                return default
            else:
                raise ValueError(
                    "Option '%s' is required for %s field" % (key, cls.NAME)
                )
        value = json_obj.pop(key)
        jtype = json.Type(value)
        if jtype is json.Object:
            raise TypeError("Field options cannot be json Objects")
        elif jtype is json.Array:
            if not is_array and is_array is not MAYBE:
                raise TypeError(
                    "Option '%s' of %s field cannot be an Array" % (key, cls.NAME)
                )
            coerced = value
        else:
            if is_array and is_array is not MAYBE:
                raise TypeError(
                    "Option '%s' of %s field must be an Array" % (key, cls.NAME)
                )
            coerced = [value]

        invalids = [v for v in coerced if not isinstance(v, type_)]
        if invalids:
            values = ", ".join("'%s'" % v for v in invalids)
            raise TypeError(
                "Invalid value %s for option '%s' in %s field, value(s) must be of type %s"
                % (values, key, cls.NAME, type_.__name__)
            )

        if valid_values is not None:
            invalids = [v for v in coerced if v not in valid_values]
            if invalids:
                values = ", ".join("'%s'" % v for v in invalids)
                raise ValueError(
                    "Invalid value %s for option '%s' in %s field, value(s) must be in %s"
                    % (values, key, cls.NAME, valid_values)
                )

        if len(coerced) == 1:
            return coerced[0]
        else:
            return coerced


class OptionGuiData(GuiDataBase):
    """
    Parses the json object and stores the Field object and GUI data for an Option field
    """

    TYPE = jsondb.OptionField.TYPE
    NAME = "option"

    def __init__(self, json_obj):
        super().__init__(json_obj)
        self.multi_selection = self.coerce(
            json_obj, key="multi_selection", type_=bool, default=False, is_array=False
        )
        self.operator = self.coerce(
            json_obj,
            key="operator",
            type_=str,
            default="or",
            is_array=None,
            valid_values=self.OPS,
        )
        self.field_spec = json_obj


class IntegerGuiData(GuiDataBase):
    """
    Parses the json and stores the Field object and GUI data for an Integer field
    """

    TYPE = jsondb.IntegerField.TYPE
    NAME = "integer"

    def __init__(self, json_obj):
        super().__init__(json_obj)
        self.listed = self.coerce(
            json_obj, key="listed", type_=int, default=[], is_array=True
        )
        self.comparison = self.coerce(
            json_obj,
            key="comparison",
            type_=str,
            default="eq",
            is_array=None,
            valid_values=self.COMP,
        )
        self.field_spec = json_obj


class TextGuiData(GuiDataBase):
    """
    Parsed the json and stores the Field object and GUI data for a Text field
    """

    TYPE = jsondb.TextField.TYPE

    def __init__(self, json_obj):
        super().__init__(json_obj)
        self.operator = self.coerce(
            json_obj,
            key="operator",
            type_=str,
            default=["Any", "All"],
            is_array=None,
            valid_values=self.OPS,
        )
        self.case = self.coerce(
            json_obj, key="case", type_=bool, default=[False, True], is_array=None
        )
        self.field_spec = json_obj


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
