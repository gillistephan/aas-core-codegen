"""Generate Go identifiers based on the identifiers from the meta-model"""
from typing import Union

from aas_core_codegen.common import Identifier


def enum_name(identifier: Identifier) -> Identifier:
    parts = identifier.split("_")
    return Identifier("{}".format("".join(part.capitalize() for part in parts)))


def enum_literal_name(enum_name: str, literal_name: str) -> str:
    return "{}".format("" + enum_name + literal_name.capitalize())


def struct_name(identifier: Identifier) -> Identifier:
    parts = identifier.split("_")
    return Identifier("{}".format("".join(part.capitalize() for part in parts)))


def property_name(identifier: Identifier) -> Identifier:
    parts = identifier.split("_")
    return Identifier("{}".format("".join(part.capitalize() for part in parts)))


def variable_name(identifier: Identifier) -> Identifier:
    parts = identifier.split("_")
    if len(parts) == 1:
        return Identifier(parts[0].lower())
    return Identifier(
        "{}{}".format(
            parts[0].lower(), "".join((part.capitalize()) for part in parts[1:])
        )
    )
