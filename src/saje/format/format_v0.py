"""
Parser for the version 0 of the SAJE format
"""

# standard library import
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Union, NewType

# third-party import
from pheres import JSONable, jsonable
from pheres import JSONValue, JSONArray, JSONObject, JSONType
from pheres.core import _VirtualValue, _VirtualArray, _VirtualObject, _VirtualClass
import pheres as ph

# Type Aliases
HTML = NewType("HTML", str)

@jsonable[None](after="ItemFormatter")
class DefaultItemFormatter:
    def __init__(self, value=None):
        pass

    def to_json(self):
        return None

    def format(self, /, item) -> HTML:
        return ph.dumps(item, indent=2)


@dataclass
@jsonable[str](after="ItemFormatter")
class StringItemFormatter(JSONable):
    string: str

    def to_json(self):
        return self.string

    def format(self, /, item) -> HTML:
        return self.string.format(
            **{".".join(flat_key): value for flat_key, value in ph.flatten(item)}
        )


@jsonable.Array["ItemFormatter", ...](after="ItemFormatter")
class ArrayItemFormatter(JSONable):
    formatters: List["ItemFormatter"]

    def __init__(self, *formatters):
        self.formatters = formatters

    def to_json(self):
        return self.formatters

    def format(self, /, item) -> HTML:
        return "".join(formatter.format(item) for formatter in self.formatters)


@dataclass(frozen=True)
@jsonable(after="ItemFormatter")
class TableItemFormatter(JSONable):
    key: str
    table: Dict[str, "ItemFormatter"]

    def __post_init__(self, /) -> None:
        if "" not in self.table:
            raise ValueError(
                "TableItemFormatter requires a default formatter under the empty key"
            )

    def format(self, /, item) -> HTML:
        formatter = self.table[""]
        if ph.has(item, self.key):
            if (value := ph.get(item, self.key)) in self.table:
                formatter = self.table[value]
        return formatter.format(item)


@dataclass(frozen=True)
@jsonable(after="ItemFormatter")
class ForItemFormatter:
    forall: str
    display_string: "ItemFormatter"
    separator: str = ""

    def format(self, /, item) -> HTML:
        return self.separator.join(
            self.display_string.format(elem) for elem in ph.get(item, self.forall, [])
        )


ItemFormatter = Union[ # pylint: disable=unsubscriptable-object
    DefaultItemFormatter, StringItemFormatter, ArrayItemFormatter, TableItemFormatter, ForItemFormatter
]
ph.register_forward_ref("ItemFormatter", ItemFormatter)

@dataclass
@jsonable
class Format_v0(JSONable):
    version: str
    name: str = None
    display_string: ItemFormatter = DefaultItemFormatter
    fields: JSONArray = field(default_factory=list)
    data: List[JSONObject] = field(default_factory=list)

print("--- NOW ISINSTANCE() OK ---")

for virtual in (_VirtualValue, _VirtualArray, _VirtualObject, _VirtualClass):
    print(f"issubclass({ArrayItemFormatter.__name__}, {virtual.__name__}) =", issubclass(ArrayItemFormatter, virtual))
print(ArrayItemFormatter._JTYPE)

with open("./examples/example.json") as f:
    print(Format_v0.from_json(f))
