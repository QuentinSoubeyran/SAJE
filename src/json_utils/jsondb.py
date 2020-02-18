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
import enum
import copy
import warnings

# Local modules
from ..json_utils import jsonplus as json

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = "0.1.0"
__maintainer__ = "Quentin Soubeyran"
__status__ = "beta"


class ValueSet(set):
    pass


class Comparison(enum.Enum):
    LT = (("lt", "<"), lambda x, y: x < y)
    LEQ = (("leq", "<="), lambda x, y: x <= y)
    EQ = (("eq", "=", "=="), lambda x, y: x == y)
    NEQ = (("neq", "!="), lambda x,y: x!=y)
    GEQ = (("geq", ">="), lambda x, y: x >= y)
    GT = (("gt", ">"), lambda x, y: x > y)

    def __new__(cls, aliases, function):
        obj = object.__new__(cls)
        obj._value_ = aliases[-1]
        obj.aliases = aliases
        obj.compare = function
        return obj

    @classmethod
    def _missing_(cls, value):
        s = str(value).lower()
        for member in cls:
            if s in member.aliases:
                return member


class Operator(enum.Enum):
    AND = (("and", "all"), all)
    OR = (("or", "any"), any)

    def __new__(cls, aliases, function):
        obj = object.__new__(cls)
        obj._value_ = aliases[0]
        obj.aliases = aliases
        obj.function = function
        return obj
    
    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)

    @classmethod
    def _missing_(cls, value):
        string = str(value).lower()
        for member in cls:
            if string in member.aliases:
                return member


class FieldBase:
    """
    Represent a search field in a database. Base class, should not be instanciated

    Field objects represents a specific test on elements of the database
    """

    CLASSES = {}
    KEY_TRANSLATION = {}
    TYPE = None

    def __init_subclass__(cls, **kwargs):
        """
        Register subclasses into the CLASSES attribute, under the key subclass.TYPE
        """
        super().__init_subclass__(**kwargs)
        cls.CLASSES[cls.TYPE] = cls

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
        if json.has(json_obj, self.key):
            return self.test(json.get(json_obj, self.key), **kwargs)
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
        if json.Type(json_repr) is not json.Object:
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

    def __init__(self, key, values=[], optional=True):
        super().__init__(key, optional=optional)
        self.values = set(values)

    def test(self, json_value, valid_values, operator: Operator= Operator.OR):
        """
        Test if the json value is (one of) the valid value(s)

        Args:
            json_value  : the json value to test (taken by FieldBase from the object to test)
            valid_values: either a single value, or a set of values as a ValueSet object
        
        Return:
            True if json_value is (one of) the valid value, False otherwise
        """
        if isinstance(valid_values, ValueSet):
            unkown_values = valid_values - set(self.values)
            if unkown_values:
                raise ValueError(
                    "Invalid test values %s, must be included in %s"
                    % (unkown_values, self.values)
                )
            if json.Type(json_value) is json.Value:
                return json_value in valid_values
            else:
                values = set(json_value if json.Type(json_value) is json.Array else json_value.values())
                match = values & valid_values
                ops = Operator(operator) #pylint: disable=no-value-for-parameter
                if ops is Operator.OR:
                    return bool(match)
                elif ops is Operator.AND:
                    return match == valid_values
                else:
                    raise TypeError("Unhandled Operator in OptionField test() method")
        else:
            if valid_values not in self.values:
                raise ValueError(
                    "Invalid value %s: must be in %s" % (valid_values, self.values)
                )
            if json.Type(json_value) is json.Value:
                return json_value == valid_values
            else:
                values = set(json_value if json.Type(json_value) is json.Array else json_value.values())
                return valid_values in values

    def _add_json_values(self, json_repr):
        json_repr["values"] = list(self.values)

    # TODO: implement _make, using all the available values in the actual data
    #   as the value set


# FieldBase.CLASSES[OptionField.TYPE] = OptionField


class IntegerField(FieldBase):
    """
    Represent a search field for integer values
    """

    TYPE = "Integer"
    KEY_TRANSLATION = {"min": "min_", "max": "max_"}

    def __init__(self, key, min_=None, max_=None, optional=True):
        """
        Create a new IntegerField object. See FieldBase.__init__ for arguments

        Args:
            min_    : minimum value this field can compare against
            max_    : maximum value this field can compare against
        """
        super().__init__(key, optional=optional)
        self.min_ = int(min_) if min_ is not None else None
        self.max_ = int(max_) if max_ is not None else None

    def bounded_value(self, value):
        if self.min_ is not None and value < self.min_:
            return self.min_
        if self.max_ is not None and value > self.max_:
            return self.max_
        return value

    def test(self, json_value, value, comparison: Comparison = Comparison.EQ):
        """
        test if `json_value` fulfills this search field

        Args:
            value: the value to compare the json_value against
            comparison (optional): the comparison operation to use
                the comparison is json_value OPS value
        """
        value = int(value)
        if self.min_ is not None and value < self.min_:
            raise ValueError("Invalid value %s: must be >= %s" % (value, self.min_))
        if self.max_ is not None and value > self.max_:
            raise ValueError("Invalid value %s: must be <= %s" % (value, self.max_))
        comparison = Comparison(comparison) #pylint: disable=no-value-for-parameter
        return comparison.compare(json_value, value) 

    def _add_json_values(self, json_repr):
        if self.min_ is not None:
            json_repr["min"] = self.min_
        if self.max_ is not None:
            json_repr["max"] = self.max_


# Registed Parser
# FieldBase.CLASSES[IntegerField.TYPE] = IntegerField


class TextField(FieldBase):
    """
    Represent a Field for sub- searching
    """

    TYPE = "Text"

    def test(self, json_value, value, operator: Operator = Operator.OR):
        """
        Test if any/all subtexts are in the json value

        Args:
            value: an iterable of subtext to find in the json_value
            operator: TextField.OR, TextField.AND, "and" or "or", whether to require
                all substring (AND) or any substring (OR)
        """
        ops = Operator(operator) #pylint: disable=no-value-for-parameter
        return ops(subtxt in json_value for subtxt in value)


# FieldBase.CLASSES[TextField.TYPE] = TextField


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

    def search(self, criteria, operator: Operator = Operator.AND):
        """
        Searches the database

        Args:
            criteria: mapping from field names to dictionary of keyword arguments
                for their `test` method
            operator (optional): the operator to use between the field return values
                Operator.AND (default): all fields must be fullfilled
                Operator.OR           : a single field suffice
            
        Returns:
            A list of item from the data that fullfills the search
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
        ops = Operator(operator) #pylint: disable=no-value-for-parameter
        return [
            json_obj
            for json_obj in self.data
            if ops(field.compare(json_obj, **kwargs) for field, kwargs in field_kwargs)
        ]

    @staticmethod
    def from_json(json_db):
        if json.Type(json_db) is not json.Object:
            raise ValueError("Json representation of database must be a Json object")
        if "data" not in json_db:
            raise ValueError("Json representation of database has no `data` member")
        if "fields" not in json_db:
            raise ValueError("Json representation of database has not `fields` member")
        for name in set(json_db.keys()) - set(["data", "fields"]):
            warnings.warn("Unused key '%s' in json representation of database" % name)
        raw_data = json_db["data"]
        type_ = json.Type(raw_data)
        if type_ not in (json.Array, json.Object):
            raise ValueError(
                "Invalid json DB: `data` key must have type json array or object"
            )
        data = []
        if type_ is json.Array:
            raw_data_iter = enumerate(raw_data)
        else:
            raw_data_iter = raw_data.items()
        for name, json_obj in raw_data_iter:
            if json.Type(json_obj) is not json.Object:
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
