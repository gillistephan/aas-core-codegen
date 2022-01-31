import io
import textwrap
from typing import Tuple, Optional, List

from icontract import ensure, require

from aas_core_codegen import intermediate, specific_implementations
from aas_core_codegen import golang
from aas_core_codegen.common import Error, Identifier, Stripped, assert_never
import aas_core_codegen.golang.naming as golang_naming
from aas_core_codegen.golang import (
    common as golang_common,
    description as golang_description,
)


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_enum(
    enum: intermediate.Enumeration,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """
    Generate the Go code for the enum in the meta-model.

    For each enum in the meta-model, a new type of type int32 is created.
    Enum literals are modeled using constants, beginning with 0.
    For stringification and lookup, a map of type map[<enum>]string and map[string]<enum>
    is generated.
    """
    writer = io.StringIO()

    if enum.description is not None:
        comment, error = golang_description.generate_comment(enum.description)
        if error:
            return None, error

        assert comment is not None
        writer.write(f"{comment} \n")

    name = golang_naming.enum_name(enum.name)

    if len(enum.literals) == 0:
        writer.write(Stripped(f"type {name} int32"))
        return Stripped(writer.getvalue()), None

    # Block declare type
    writer.write(f"type {name} int32")
    writer.write("\n\n")

    cache = []  # Type: List[str]

    # Block Constants
    # Open
    writer.write("const (")
    for i, literal in enumerate(enum.literals):

        cache.append(literal.name)
        full_name = f"{name}_{literal.name}"
        if i == 0:
            writer.write(f"{full_name} {name} = iota")
            writer.write("\n")
        else:
            writer.write(f"{full_name}")
            writer.write("\n")

    # Close
    writer.write(")")
    writer.write("\n\n")

    # Block name map
    # Open
    writer.write(f"var {name}_name = map[{name}]string {{")
    writer.write("\n")
    for i, v in enumerate(cache):
        writer.write(f'{i}: "{v}",')
        writer.write("\n")
    # Close
    writer.write("}")
    writer.write("\n\n")

    # Block value map
    # Open
    writer.write(f"var {name}_value = map[string]{name} {{")
    writer.write("\n")
    for i, v in enumerate(cache):
        writer.write(f'"{v}": {i},')
        writer.write("\n")
    # Close
    writer.write("}")
    writer.write("\n\n")

    # Stringer interface
    writer.write(
        textwrap.dedent(
            f"""func (s {name}) String() string {{ 
                return {name}_name[s] 
            }}"""
        )
    )

    return Stripped(writer.getvalue()), None


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_interface(
    interface: intermediate.Interface,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """
    Generate the Go code for the interface in the meta-model.

    Go does not implement Generics. Types are just printed for reference.
    For each inteface having implementers we generate a seperate type <name>Data for
    encoding and decoding holding all possible types.

    E.g. type SubmodelElementData struct {
        *SubmodelElement
        *SubmodelElementList
        *SubmodelElementListStruct
    }
    """
    writer = io.StringIO()
    name = golang_naming.struct_name(interface.name)

    writer.write(f"type {name} struct {{")
    writer.write("\n")

    for prop in interface.properties:
        prop_type = golang_common.generate_type(type_annotation=prop.type_annotation)
        prop_name = golang_naming.property_name(prop.name)
        writer.write(f"{prop_name} {prop_type}")
        writer.write("\n")

    writer.write("}")
    writer.write("\n\n")

    if len(interface.implementers) > 0:
        writer.write(
            f"// {name}Data is a generic data type used for encoding and decoding {name} \n // holding all possible types as pointer \n"
        )
        writer.write(f"type {name}Data struct {{")
        writer.write("\n")

        # NOTE: implementers itself can be abstract:
        # e.g. SubmodelElement --> Event (Abstract) --> BasicEvent
        for impl in interface.implementers:
            name = golang_naming.struct_name(impl.name)
            writer.write(f"*{name}")
            writer.write("\n")

        writer.write("\n")
        writer.write("}")

    return writer.getvalue(), None


@require(lambda cls: not cls.is_implementation_specific)
@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_class(
    cls: intermediate.ConcreteClass,
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

    struct_name = golang_naming.struct_name(cls.name)

    # Type Block
    # Start
    writer.write(f"type {struct_name} struct {{")
    writer.write("\n")

    for prop in cls.properties:
        prop_type = golang_common.generate_type(type_annotation=prop.type_annotation)
        prop_name = golang_naming.property_name(prop.name)
        writer.write(f"{prop_name} {prop_type}")
        writer.write("\n")
    # End
    writer.write("}")

    return writer.getvalue(), None


def generate(
    symbol_table: intermediate.SymbolTable,
    package_name: Stripped,
    spec_impls: specific_implementations.SpecificImplementations,
) -> Tuple[Optional[str], Optional[List[Error]]]:
    """Generate the Golang code of the structures based on the symbol table."""

    abstract_usages = golang_common.find_abstract_class_usages(
        symbol_table=symbol_table
    )

    blocks = [golang_common.WARNING]  # type List[Rstripped]
    errors = []  # type List[Error]

    # package_name
    blocks.append(f"package {package_name}")

    for something in golang_common.over_enumerations_classes_and_interfaces(
        symbol_table
    ):
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
                    f"The implementation is missing",
                    f"for the implementation-specific class: {impl_key}",
                )
                break
        else:
            if isinstance(something, intermediate.Enumeration):
                code, error = _generate_enum(enum=something)
            elif isinstance(something, intermediate.Interface):
                if something.name in abstract_usages:
                    code, error = _generate_interface(interface=something)
                else:
                    # set to empty string to allow assertion below
                    code = ""
            elif isinstance(something, intermediate.ConcreteClass):
                code, error = _generate_class(cls=something)
            else:
                assert_never(something)

        assert (code is not None) ^ (error is not None)

        if error is not None:
            errors.append(error)
        else:
            assert code is not None
            blocks.append(Stripped(code))

        if len(errors) > 0:
            return None, errors

        writer = io.StringIO()
        for i, b in enumerate(blocks):
            if i > 0:
                writer.write("\n\n")
            writer.write(b)

    return writer.getvalue(), None
