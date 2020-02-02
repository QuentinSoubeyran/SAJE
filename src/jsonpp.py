#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Small library that extends python's built-in json library with various utilities
"""
# Built-in modules
import enum

from json import *
from collections.abc import Mapping, Sequence

__author__ = "Quentin Soubeyran"
__copyright__ = "Copyright 2020, SAJE project"
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Quentin Soubeyran"
__status__ = "alpha"

# keep the type
set_type = set

class JsonTypeError(BaseException):
    pass


class Type(enum.Enum):
    """
    Represents the JSON type of a python structure as returned by the json module.
    """

    Object = enum.auto()
    Array = enum.auto()
    Value = enum.auto()

    @staticmethod
    def of(json_obj):
        """Return the JSON type of an object"""
        if isinstance(json_obj, Mapping):
            return Type.Object
        elif (not isinstance(json_obj, str)) and isinstance(json_obj, Sequence):
            return Type.Array
        elif isinstance(json_obj, int) or isinstance(json_obj, str):
            return Type.Value
        else:
            raise JsonTypeError("Type %s is invalid in JSON" % type(json_obj))

    @staticmethod
    def is_numeric(json_obj):
        if isinstance(json_obj, int) or isinstance(json_obj, float):
            return True
        return False


def flatten(json_obj: dict):
    """
    Flatten a json as a list of key-value pairs where the key is the list of keys from the root to the value
    """

    def walker(flat_json, keys, json_obj):
        type_ = Type.of(json_obj)
        if type_ is Type.Object:
            for key, subjson in json_obj.items():
                walker(flat_json, keys + (key,), subjson)
        elif type_ is Type.Array:
            for index, subjson in enumerate(json_obj):
                walker(flat_json, keys + (index,), subjson)
        elif type_ is Type.Value:
            flat_json.append((keys, json_obj))
        else:
            raise JsonTypeError("Unknown json type: %s" % type_)

    flat_json = []
    walker(flat_json, tuple(), json_obj)
    return flat_json


def expand(flat_json: list, dict_only=False):
    def rec(flat, pkey):
        if not len(flat):
            raise ValueError("cannot convert empty flat json to json")
        first_keylist = flat[0][0]
        last_keylist = flat[-1][0]
        if not len(first_keylist):
            # if the first keylist is empty, i.e. we got a json value
            if len(flat) > 1:
                raise ValueError(f"Multiple json values for flat key {pkey}")
            return flat[0][1]
        if dict_only or isinstance(first_keylist[0], str):
            json_obj = {}
            for keylist, value in flat:
                json_obj.setdefault(keylist[0], []).append((keylist[1:], value))
            for key, group in json_obj.items():
                json_obj[key] = rec(group, pkey + (key,))
            return json_obj
        elif isinstance(first_keylist[0], int):
            json_array = [[] for _ in range(int(last_keylist[0]) + 1)]
            for keylist, value in flat:
                json_array[keylist[0]].append((keylist[1:], value))
            for index, group in enumerate(json_array):
                json_array[index] = rec(group, pkey + (index,))
            return json_array
        else:
            raise TypeError(
                f"Invalid json key of type {type(first_keylist[0])} under key {pkey}"
            )

    return rec(sorted(flat_json, key=lambda x: x[0]), tuple())


def compact(json_obj, sep="."):
    """
    Returns a new dict-only json that is a copy of `json_obj` where keys with only one element are
    merged with their parent key
    """
    ret = {}
    for k, v in json_obj.items():
        if Type.of(v) is Type.Array:
            v = {str(i): elem for i, elem in enumerate(v)}
        if Type.of(v) is Type.Object:
            v = compact(v, sep)
            if len(v) == 1:
                kp, v = next(iter(v.items()))
                ret[f"{k!s}{sep}{kp!s}"] = v
                continue
        ret[k] = v
    return ret


class JsonDifferenceError(Exception):
    pass


class CommonKey:
    """Class representing a common json key with all the keys from the root to the value"""

    def __init__(self, keys, l_value, r_value):
        self.keys = keys
        self.l_value = l_value
        self.r_value = r_value


class DiffKey:
    """Class representing a json key with different value type"""

    def __init__(self, keys, l_json, r_json):
        self.keys = keys
        self.l_json = l_json
        self.r_json = r_json


def compare_jsons(
    left_json,
    right_json,
    common_callback=CommonKey,
    diff_callback=lambda *args: None,
    strict_keys=False,
    strict_types=False,
):
    """
    Compare two jsons and call the appropriate callback on shared or different keys, gathering the results of
    the callbacks in the returned list. If a callback returns 'None', the key is ignored.
    By default, returns a list of the common keys represented by CommonKey instances.

    left_json       - the left json to compare
    right_json      - the right json to compare
    common_callback - the callable to call on common keys, with arguments
                        -- keys   : a tuple representing the nested keys to the common value
                        -- l_value: the value of the shared key in left_json
                        -- r_value: the value of the shared key in right_json
    diff_callback   - the callable to call on differing keys, with the same arguments as above. Will get
                        called at all points where the keys differs
    strict_keys     - wether to raise a JsonDifferenceError when right_json contains a key not present in left_json
    strict_types    - wether to raise a JsonDifferenceError when right_json contains a shared key with a different
                        json type than the same key in left_json
    """
    # Json traversal functions
    def array_compare(common, key, l_array, r_array):
        if strict_keys and len(l_array) != len(r_array):
            raise JsonDifferenceError(
                f"left json-array and right json-array under key {key} do not have the same lenght: {len(l_array)} and {len(r_array)}"
            )
        for index in range(min(len(l_array), len(r_array))):
            json_compare(common, key + (index,), l_array[index], r_array[index])

    def object_compare(common, key, l_object, r_object):
        l_keys, r_keys = set_type(l_object.keys()), set_type(r_object.keys())
        if strict_keys and not (r_keys <= l_keys):
            raise JsonDifferenceError(
                f"right json-object under key {key} has keys not present in left json-object: {r_keys - l_keys}"
            )
        for k in r_keys:
            json_compare(common, key + (k,), l_object[k], r_object[k])

    def json_compare(common, key, l_json, r_json):
        l_type = Type.of(l_json)
        r_type = Type.of(r_json)
        if l_type is r_type is Type.Value:
            result = common_callback(key, l_json, r_json)
            if result is not None:
                common.append(result)
        elif l_type is r_type is Type.Array:
            array_compare(common, key, l_json, r_json)
        elif l_type is r_type is Type.Object:
            object_compare(common, key, l_json, r_json)
        elif strict_types:
            raise JsonDifferenceError(
                f"Value of key {key} has type {Type.of(l_json)} in the left json but type {Type.of(r_json)} in right json"
            )
        else:
            result = diff_callback(key, l_json, r_json)
            if result is not None:
                common.append(result)
        return common

    return json_compare([], tuple(), left_json, right_json)


def get(obj, key, sep="."):
    if isinstance(key, str):
        key = key.split(sep)
    if len(key) == 0:
        raise KeyError("empty Json key")
    elif len(key) == 1:
        return obj[key[0]]
    else:
        return get(obj[key[0]], key[1:])


def has(obj, key, sep="."):
    if isinstance(key, str):
        key = key.split(sep)
    try:
        get(obj, key)
        return True
    except KeyError:
        return False


def set(obj, key, value, sep="."):
    if isinstance(key, str):
        key.split(sep)
    if len(key) == 0:
        raise KeyError
    elif len(key) == 1:
        obj[key[0]] = value
    else:
        set(obj[key[0]], key[1:], value)
