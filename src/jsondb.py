#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module to represents simple database in JSON format and associated search options

JSON-like objects mean python objects representing JSON object as produced by the
built-in `json` module
Data is represented by a JSON-like list of arbitrary JSON-like object
A `Field` is a search option on the data, i.e. a test to do to select data fulfilling
certain criteria
A `Database` represents an association of data and fields to search on that data
"""
# Built-in modules
import copy
import warnings

# Local modules
from . import jsonpp

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Quentin Soubeyran"
__status__ = "alpha"


class FieldBase:
    """
    Represent a search field in a database. Base class, should not be instanciated

    Field objects represents a specific test on elements of the database
    """

    CLASSES = {}
    KEY_TRANSLATION = {}
    TYPE = None

    def __init__(self, key, optional=True):
        """
        Create a new Field object to search through JSON-like objects
        
        Args:
            key: the JSON path inside object that leads to the value this fields compares to
            optional: whether this field should always check or allows any item is no value is provided
        """
        self.key = key
        self.optional = bool(optional)

    def compare(self, json_obj, accept_missing=True, **kwargs):
        """
        Returns wether the json object matches with the value for this field

        Args:
            json_obj        : the JSON-object on which to test a property
            accept_missing  : if `json_obj` has no value under the `key` specified
                at Field object creation, whether to accept it or not
            kwargs          : subclass-specific additionals arguments for the test. Usually
                include `value` which is the value to test against
        
        Returns:
            True if the object passes the test, false otherwise
        """
        if jsonpp.has(json_obj, self.key):
            return self.test(jsonpp.get(json_obj, self.key), **kwargs)
        else:
            return accept_missing

    def test(self, json_value, **kwargs):
        """
        Performs the test on the value of the JSON object. Must be defined by subclass
        """
        raise NotImplementedError(
            "Subclasses of FieldBase must implement the test() method"
        )

    def to_json(self):
        """
        Return a JSON-like object (that can be written to file using the `json` module)
        that represents this Field object
        """
        if type(self).TYPE is None:
            raise NotImplementedError(
                "Subclasses of FieldBase must have a class attribute TYPE"
            )
        json_repr = {"type": type(self).TYPE, "key": self.key}
        if self.optional:
            json_repr["optional"] = True
        self._add_json_values(json_repr)
        return json_repr

    def _add_json_values(self, json_repr):
        """
        Add subclass-specific element to the json representation of that field.
        Must be defined by subclass
        """
        pass

    @staticmethod
    def from_json(json_repr, data=[]):
        """
        Parses a json-like object into a field object

        Args:
            json_repr: the json object (object returns by json.load methods) representing this field
            data    : the list of elements this field will search on. Allows to take info from that
        
        Returns:
            A object of a subclass of FieldBase as defined by the value of the `type` key of the object
        """
        if jsonpp.Type.of(json_repr) is not jsonpp.Type.Object:
            raise ValueError("Invalid field json representation: must be a json object")
        if "type" not in json_repr:
            raise ValueError("Invalid field json representation: must have key `type`")
        type_ = json_repr["type"]
        if type_ not in FieldBase.CLASSES:
            raise TypeError("Unknown field type `%s`" % type_)
        return FieldBase.CLASSES[type_]._make(json_repr, data=data)

    @classmethod
    def _make(cls, json_repr, data=[]):
        """
        Create an instance of the FieldBase subclass from a json representation
        Can be overridden by the subclass, the default is just to pass the json_obj to __init__
        """
        return cls(
            **{
                cls.KEY_TRANSLATION.get(key, key): value
                for key, value in json_repr.items()
                if key not in ("type",)
            }
        )


class OptionField(FieldBase):
    """
    Represent a search field that may take one value from a set of possible values
    """

    TYPE = "Option"

    def __init__(self, key, values=[], multi_selection=False, optional=True):
        super().__init__(key, optional=optional)
        self.values = set(values)
        self.multi_selection = multi_selection

    def test(self, json_value, value_or_set):
        """
        Test if the json value is (one of) the valid value(s)

        Args:
            json_value  : the json value to test (taken by FieldBase from the object to test)
            value_or_set: depending of the value of self.multi_selection, a single value OR an Iterable of values
        
        Return:
            True if json_value is (one of) the valid value, False otherwise

        Warning:
            if self.multi_selection is True, value_or_set *must* be an iterable of values, even if
                only one is valid
        """
        if self.multi_selection:
            valid_values = set(value_or_set)
            unkown_values = valid_values - set(self.values)
            if unkown_values:
                raise ValueError(
                    "Invalid test values %s, must be included in %s"
                    % (unkown_values, self.values)
                )
            return json_value in valid_values
        else:
            if value_or_set not in self.values:
                raise ValueError(
                    "Invalid value %s: must be in %s" % (value_or_set, self.values)
                )
            return json_value == value_or_set

    def _add_json_values(self, json_repr):
        json_repr["values"] = list(self.values)
        if self.multi_selection:
            json_repr["multi_selection"] = True

    # TODO: implement _make, using all the available values in the actual data
    #   as the value set


FieldBase.CLASSES["Option"] = OptionField


class IntegerField(FieldBase):
    """
    Represent a search field for integer values
    """

    TYPE = "Integer"
    KEY_TRANSLATION = {"min": "min_", "max": "max_"}

    def __init__(
        self,
        key,
        min_=None,
        max_=None,
        listed=[],
        optional=True,
        lower_bound=False,
        upper_bound=False,
    ):
        """
        Create a new IntegerField object. See FieldBase.__init__ for arguments

        Args:
            min_    : minimum value this field can compare against
            max_    : maximum value this field can compare against
            listed  : unsed, used for GUI implementation pruposes. The list
                of value to propose with a drop-down menu for instance
        """
        if lower_bound and upper_bound:
            lower_bound = upper_bound = False
        super().__init__(key, optional=optional)
        self.upper_bound = bool(upper_bound)
        self.lower_bound = bool(lower_bound)
        self.min_ = int(min_)
        self.max_ = int(max_)
        self.listed = list(listed)
    
    def bounded_value(self, value):
        if self.min_ is not None and value < self.min_:
            return self.min_
        if self.max_ is not None and value > self.max_:
            return self.max_
        return value

    def test(self, json_value, value):
        value = int(value)
        if self.min_ is not None and value < self.min_:
            raise ValueError("Invalid value %s: must be >= %s" % (value, self.min_))
        if self.max_ is not None and value > self.max_:
            raise ValueError("Invalid value %s: must be <= %s" % (value, self.max_))
        if self.lower_bound:
            return json_value >= value
        elif self.upper_bound:
            return json_value <= value
        else:
            return json_value == value

    def _add_json_values(self, json_repr):
        if self.min_ is not None:
            json_repr["min"] = self.min_
        if self.max_ is not None:
            json_repr["max"] = self.max_
        if self.lower_bound:
            json_repr["lower_bound"] = True
        if self.upper_bound:
            json_repr["upper_bound"] = True
        if self.listed:
            json_repr["listed"] = self.listed


# Registed Parser
FieldBase.CLASSES["Integer"] = IntegerField


class TextField(FieldBase):
    """
    Represent a Field for sub- searching
    """

    TYPE = "Text"
    OR = any
    AND = all

    def test(self, json_value, value, operator=OR):
        """
        Test if any/all subtexts are in the json value

        Args:
            value: an iterable of subtext to find in the json_value
            operator: TextField.OR, TextField.AND, "and" or "or", whether to require
                all substring (AND) or any substring (OR)
        """
        if operator in ("AND", "And", "and", "ALL", "All", "all"):
            operator = TextField.AND
        elif operator in ("OR", "Or", "or", "ANY", "Any", "any"):
            operator = TextField.OR
        return operator(subtxt in json_value for subtxt in value)


FieldBase.CLASSES["Text"] = TextField


class Database:
    """
    A class to specify data and how to search on that data in JSON format
    """

    def __init__(self, data=[], fields={}):
        """
        Create a new database object

        Args:
            data: a list of JSON-like python object to search in
            search_fields: a mapping from names (str) to Field objects, represents the
                search fields
        """
        self.data = data
        self.fields = fields

    def search(self, criteria):
        """
        Searches the database

        Args:
            criteria: mapping from field names to dictionary of keyword argument
                for there `test` method
        """
        for field_name, field in self.fields.items():
            if not field.optional and field_name not in criteria:
                raise ValueError("Field %s must be specified" % field_name)
        if set(criteria) - set(self.fields):
            raise ValueError(
                "Unknown search field %s" % set(criteria) - set(self.fields)
            )
        field_kwargs = [
            (self.fields[field_name], kwargs) for field_name, kwargs in criteria.items()
        ]
        return [
            json_obj
            for json_obj in self.data
            if all(field.compare(json_obj, **kwargs) for field, kwargs in field_kwargs)
        ]

    @staticmethod
    def from_json(json_db):
        if jsonpp.Type.of(json_db) is not jsonpp.Type.Object:
            raise ValueError("Json representation of database must be a Json object")
        if "data" not in json_db:
            raise ValueError("Json representation of database has no `data` member")
        if "fields" not in json_db:
            raise ValueError("Json representation of database has not `fields` member")
        for name in set(json_db.keys()) - set(["data", "fields"]):
            warnings.warn("Unused key '%s' in json representation of database" % name)
        raw_data = json_db["data"]
        type_ = jsonpp.Type.of(raw_data)
        if type_ not in (jsonpp.Type.Array, jsonpp.Type.Object):
            raise ValueError(
                "Invalid json DB: `data` key must have type json array or object"
            )
        data = []
        if type_ is jsonpp.Type.Array:
            raw_data_iter = enumerate(raw_data)
        else:
            raw_data_iter = raw_data.items()
        for name, json_obj in raw_data_iter:
            if jsonpp.Type.of(json_obj) is not jsonpp.Type.Object:
                warnings.warn(
                    "Invalid data element %s in json db: should be a json object, was ignored"
                    % name
                )
            else:
                data.append(json_obj)
        fields = {
            name: FieldBase.from_json(json_field, data=data)
            for name, json_field in json_db["fields"].items()
        }
        return Database(data=data, fields=fields)

    def to_json(self):
        """
        Converts the database in its JSON form

        Returns:
            An object compatible with the `json` module
        """
        return {
            "fields": {
                field_name: field.to_json() for field_name, field in self.fields.items()
            },
            "data": self.data,
        }
