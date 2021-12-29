import io
import textwrap
from typing import Tuple, Iterator, Union, Optional, List
from aas_core_codegen import csharp, intermediate, specific_implementations
from aas_core_codegen.common import Error, Identifier, Rstripped, Stripped, assert_never
import aas_core_codegen.golang.naming as golang_naming
from aas_core_codegen.golang import (
    common as golang_common,
    description as golang_description,
)

# NOTE (SG, 2021-12-27) import this from csharp.common; might be provided as general utility to all code generators
from aas_core_codegen.csharp.common import over_enumerations_classes_and_interfaces


from icontract import ensure, require


# NOTE (SG, 2021-12-27)
# Golang does not know the concept of enums.
# The idiomatic Go way to represent enums is to define a new type with int32/64 as the base type.
#
# type Identifier int32
#
# Enum-literals are modeled as constants with the newly created type.
#
# const (
#   Identifier_IRDI     Identifier = iota
#   Identifier_IRI
# )
#
# The go way to assign int values to the constants is by using the ``iota`` keyword.
# It prevents from inadvertently assign the same value to more than one const.
# Due to automatic code generation, we can assign the values directly?
#
# For fast lookups during de-/encoding we provide name and value maps like:
#
# var Identifier_name = map[Identifier]string{
#   0: "IRDI",
#   1: "IRI",
# }
#
# var Identifier_value = map[string]Identifier{
#   "IRDI": 0,
#   "IRI":  1,
# }
#
# In the meta-model, different enums can have the same literal value (e.g. AssetKind and ModelingKind).
# When modeling literals as constants, this would lead to naming collisions.
# To avoid that, the actual constants are prefixed with the enum name.
#
# e.g. ModelingKind_TEMPLATE; AssetKind_TEMPLATE


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_enum(
    enum: intermediate.Enumeration,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """
    Generate the Go code for the enum in the meta-model.
    """

    writer = io.StringIO()
    if enum.description is not None:
        comment, error = golang_description.generate_comment(enum.description)
        if error:
            return None, error

        assert comment is not None
        writer.write(comment)
        writer.write("\n")

    name = golang_naming.enum_name(enum.name)

    if len(enum.literals) == 0:
        writer.write(f"type {name} int32 \n")
        return Stripped(writer.getvalue()), None

    writer.write(f"type {name} int32 \n\n")

    writer.write(f"const ( \n")

    cache = []  # Type: List[str]
    for i, literal in enumerate(enum.literals):
        literal_name = literal.name.upper()
        cache.append(literal_name)

        full_name = f"{name}_{literal_name}"
        if i == 0:
            writer.write(f"{full_name} {name} = iota")
        else:
            writer.write(f"\n{full_name}")
    writer.write(f") \n\n")

    writer.write(f"var {name}_name = map[{name}]string{{ \n")
    for i, v in enumerate(cache):
        writer.write(f'{i}: "{v}", \n')
    writer.write(f"}} \n\n")

    writer.write(f"var {name}_value = map[string]{name}{{ \n")
    for i, v in enumerate(cache):
        writer.write(f'"{v}": {i}, \n')
    writer.write(f"}} \n")

    # Stringer interface
    writer.write(f"func (s {name}) String() string {{ \n")
    writer.write(f"return {name}_name[s] \n")
    writer.write(f"}} \n\n")

    # GetValue
    writer.write(f"func Get{name}Value(n string) {name} {{\n")
    writer.write(f"return {name}_value[n] \n")
    writer.write(f"}} \n\n")

    # GetName
    writer.write(f"func Get{name}Name(v {name}) string {{ \n")
    writer.write(f"return {name}_name[v] \n")
    writer.write(f"}}")

    return Stripped(writer.getvalue()), None


# NOTE: (SG, 2021-12-27)
# Golang does not know the concept of interfaces. The closest what we can get is
# type embedding. To embedd a type just pass it as a namless parameter within another type
# so that all exported parameters and methods are accessible.

# e.g. type MyStruct struct {
#   fancy       string
# }
#
# type MySecondStruct struct {
#   MyStruct
#   fancy2      string
# }
#
# For the time being, we just render the interfaces as type <Name> struct {} and all the properties.
#


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_interface(
    interface: intermediate.Interface,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """
    Generate Go code for the given interface
    """
    writer = io.StringIO()

    name = golang_naming.class_name(interface.name)
    writer.write(f"type {name} struct {{ \n")

    """
    This part would be used, if we use type embedding

    inheritances = [inheritance.name for inheritance in interface.inheritances]
    inheritance_names = list(map(golang_naming.class_name, inheritances))
    if len(inheritance_names) > 0:
        for i, name in enumerate(inheritance_names):
            if i > 0:
                writer.write("\n")
            writer.write(f"{name} \n")
    """

    for prop in interface.properties:
        prop_type = golang_common.generate_type(type_annotation=prop.type_annotation)
        prop_name = golang_naming.property_name(prop.name)
        writer.write(f"{prop_name} {prop_type}\n")

    writer.write("}")
    return Stripped(writer.getvalue()), None


@require(lambda cls: not cls.is_implementation_specific)
@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_class(
    cls: intermediate.ConcreteClass,
    spec_impls=specific_implementations.SpecificImplementations,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """
    Generate Go code for the given concrete class ``cls``.
    """

    writer = io.StringIO()

    if cls.description is not None:
        comment, error = golang_description.generate_comment(cls.description)
        if error:
            return None, error

        assert comment is not None

        writer.write(comment)
        writer.write("\n")

    name = golang_naming.class_name(cls.name)
    writer.write(f"type {name} struct {{ \n")

    """ 
    This part would be used, if we use type embedding

    
    inheritances = [inheritance.name for inheritance in cls.inheritances]
    inheritance_names = list(map(golang_naming.class_name, inheritances))

    
    if len(inheritance_names) > 0:
        for i, name in enumerate(inheritance_names):
            if i > 0:
                writer.write("\n")
            writer.write(f"{name} \n")
     """

    for prop in cls.properties:

        prop_type = golang_common.generate_type(type_annotation=prop.type_annotation)
        prop_name = golang_naming.property_name(prop.name)
        writer.write(f"{prop_name} {prop_type} \n")

    writer.write("}")

    return Stripped(writer.getvalue()), None


def generate(
    symbol_table: intermediate.SymbolTable,
    package_name: Stripped,
    spec_impls: specific_implementations.SpecificImplementations,
) -> Tuple[Optional[str], Optional[List[Error]]]:
    """Generate the Golang code of the structures based on the symbol table."""

    blocks = [golang_common.WARNING]  # type List[Rstripped]
    errors = []  # type List[Error]

    # package_name
    blocks.append(Stripped(f"package {package_name}"))

    for something in over_enumerations_classes_and_interfaces(symbol_table):
        code = None  # type: Optional[Stripped]
        error = None  # type: Optional[Error]

        if (
            isinstance(something, intermediate.Class)
            and something.is_implementation_specific
        ):
            impl_key = specific_implementations.ImplementationKey(
                f"{something.name}.txt"
            )
            code = spec_impls.get(impl_key)
            if code is None:
                error = Error(
                    something.parsed.node,
                    f"The implementation is missing "
                    f"for the implementation-specific class: {impl_key}",
                )
        else:
            if isinstance(something, intermediate.Enumeration):
                code, error = _generate_enum(enum=something)

            elif isinstance(something, intermediate.Interface):
                code, error = _generate_interface(interface=something)

            elif isinstance(something, intermediate.ConcreteClass):
                code, error = _generate_class(cls=something)

            else:
                assert_never(something)

        assert (code is None) ^ (error is None)
        if error is not None:
            errors.append(error)
        else:
            assert code is not None
            blocks.append(Rstripped(code))

        if len(errors) > 0:
            return None, errors

        out = io.StringIO()

        for i, b in enumerate(blocks):
            if i > 0:
                out.write("\n\n")
            out.write(b)
        out.write("\n")

    return out.getvalue(), None
