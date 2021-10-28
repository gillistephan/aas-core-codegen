"""Generate C# identifiers based on the identifiers from the meta-model."""

from aas_core_csharp_codegen.common import Identifier


def interface_name(identifier: Identifier) -> Identifier:
    """
    Generate a C# interface name based on its meta-model ``identifier``.

    >>> interface_name(Identifier("something"))
    'ISomething'

    >>> interface_name(Identifier("URL_to_something"))
    'IUrlToSomething'
    """
    parts = identifier.split('_')

    return Identifier("I{}".format(''.join(part.capitalize() for part in parts)))


def enum_name(identifier: Identifier) -> Identifier:
    """
    Generate a C# name for an enum based on its meta-model ``identifier``.

    >>> enum_name(Identifier("something"))
    'Something'

    >>> enum_name(Identifier("URL_to_something"))
    'UrlToSomething'
    """
    parts = identifier.split('_')

    return Identifier("{}".format(''.join(part.capitalize() for part in parts)))


def enum_literal_name(identifier: Identifier) -> Identifier:
    """
    Generate a C# name for an enum literal based on its meta-model ``identifier``.

    >>> enum_literal_name(Identifier("something"))
    'Something'

    >>> enum_literal_name(Identifier("URL_to_something"))
    'UrlToSomething'
    """
    parts = identifier.split('_')

    return Identifier("{}".format(''.join(part.capitalize() for part in parts)))


def class_name(identifier: Identifier) -> Identifier:
    """
    Generate a C# name for a class based on its meta-model ``identifier``.

    >>> enum_name(Identifier("something"))
    'Something'

    >>> enum_name(Identifier("URL_to_something"))
    'UrlToSomething'
    """
    parts = identifier.split('_')

    return Identifier("{}".format(''.join(part.capitalize() for part in parts)))


def property_name(identifier: Identifier) -> Identifier:
    """
    Generate a C# name for a public property based on its meta-model ``identifier``.

    >>> property_name(Identifier("something"))
    'Something'

    >>> property_name(Identifier("something_to_URL"))
    'SomethingToUrl'
    """
    parts = identifier.split('_')

    if len(parts) == 1:
        return Identifier(parts[0].capitalize())

    return Identifier(
        "{}{}".format(
            parts[0].capitalize(),
            ''.join(part.capitalize() for part in parts[1:])))


def private_property_name(identifier: Identifier) -> Identifier:
    """
    Generate a C# name for a private property based on the ``identifier``.

    >>> private_property_name(Identifier("something"))
    '_something'

    >>> private_property_name(Identifier("something_to_URL"))
    '_somethingToUrl'
    """
    parts = identifier.split('_')

    if len(parts) == 1:
        return Identifier(f"_{Identifier(parts[0].lower())}")

    return Identifier(
        "_{}{}".format(
            parts[0].lower(),
            ''.join(part.capitalize() for part in parts[1:])))


def method_name(identifier: Identifier) -> Identifier:
    """
    Generate a C# name for a member method based on its meta-model ``identifier``.

    >>> method_name(Identifier("do_something"))
    'DoSomething'

    >>> method_name(Identifier("do_something_to_URL"))
    'DoSomethingToUrl'
    """
    parts = identifier.split('_')

    if len(parts) == 1:
        return Identifier(parts[0].capitalize())

    return Identifier(
        "{}{}".format(
            parts[0].capitalize(),
            ''.join(part.capitalize() for part in parts[1:])))

def argument_name(identifier: Identifier) -> Identifier:
    """
    Generate a C# name for an argument based on its meta-model ``identifier``.

    >>> argument_name(Identifier("something"))
    'something'

    >>> argument_name(Identifier("something_to_URL"))
    'somethingToUrl'
    """
    parts = identifier.split('_')

    if len(parts) == 1:
        return Identifier(parts[0].lower())

    return Identifier(
        "{}{}".format(
            parts[0].lower(),
            ''.join(part.capitalize() for part in parts[1:])))

def variable_name(identifier: Identifier) -> Identifier:
    """
    Generate a C# name for a variable based on its meta-model ``identifier``.

    >>> variable_name(Identifier("something"))
    'something'

    >>> variable_name(Identifier("something_to_URL"))
    'somethingToUrl'
    """
    parts = identifier.split('_')

    if len(parts) == 1:
        return Identifier(parts[0].lower())

    return Identifier(
        "{}{}".format(
            parts[0].lower(),
            ''.join(part.capitalize() for part in parts[1:])))
