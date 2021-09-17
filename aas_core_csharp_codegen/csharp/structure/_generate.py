"""Generate the C# data structures from the intermediate representation."""
import io
import textwrap
import xml.sax.saxutils
from typing import Optional, Dict, List, Tuple, cast

import docutils.nodes
import docutils.parsers.rst.roles
import docutils.utils
from icontract import ensure, require

import aas_core_csharp_codegen.csharp.common as csharp_common
import aas_core_csharp_codegen.csharp.naming as csharp_naming
from aas_core_csharp_codegen import intermediate, naming
from aas_core_csharp_codegen import specific_implementations
from aas_core_csharp_codegen.common import Error, Identifier, assert_never, \
    Stripped, Rstripped


# region Checks

def _verify_structure_name_collisions(
        intermediate_symbol_table: intermediate.SymbolTable
) -> List[Error]:
    """Verify that the C# names of the structures do not collide."""
    observed_structure_names = {}  # type: Dict[Identifier, intermediate.Symbol]

    errors = []  # type: List[Error]

    for symbol in intermediate_symbol_table.symbols:
        name = None  # type: Optional[Identifier]

        if isinstance(symbol, intermediate.Class):
            name = csharp_naming.class_name(symbol.name)
        elif isinstance(symbol, intermediate.Enumeration):
            name = csharp_naming.enum_name(symbol.name)
        elif isinstance(symbol, intermediate.Interface):
            name = csharp_naming.interface_name(symbol.name)
        else:
            assert_never(symbol)

        assert name is not None
        if name in observed_structure_names:
            # TODO: test
            errors.append(
                Error(
                    symbol.parsed.node,
                    f"The C# name {name!r} "
                    f"of the meta-model symbol {symbol.name!r} collides "
                    f"with another meta-model symbol "
                    f"{observed_structure_names[name].name!r}"))
        else:
            observed_structure_names[name] = symbol

    # region Intra-structure collisions

    for symbol in intermediate_symbol_table.symbols:
        collision_error = _verify_intra_structure_collisions(intermediate_symbol=symbol)

        if collision_error is not None:
            errors.append(collision_error)

    return errors


def _verify_intra_structure_collisions(
        intermediate_symbol: intermediate.Symbol
) -> Optional[Error]:
    """Verify that no member names collide in the C# structure of the given symbol."""
    errors = []  # type: List[Error]

    if isinstance(intermediate_symbol, (intermediate.Class, intermediate.Interface)):
        observed_member_names = {}  # type: Dict[Identifier, str]

        for prop in intermediate_symbol.properties:
            prop_name = csharp_naming.property_name(prop.name)
            if prop_name in observed_member_names:
                # TODO: test
                errors.append(
                    Error(
                        prop.parsed.node,
                        f"C# property {prop_name!r} corresponding "
                        f"to the meta-model property {prop.name!r} collides with "
                        f"the {observed_member_names[prop_name]}"
                    ))
            else:
                observed_member_names[prop_name] = (
                    f"C# property {prop_name!r} corresponding to "
                    f"the meta-model property {prop.name!r}")

        for method in intermediate_symbol.methods:
            method_name = csharp_naming.method_name(method.name)

            if method_name in observed_member_names:
                # TODO: test
                errors.append(
                    Error(
                        method.parsed.node,
                        f"C# method {method_name!r} corresponding "
                        f"to the meta-model method {method.name!r} collides with "
                        f"the {observed_member_names[method_name]}"
                    ))
            else:
                observed_member_names[method_name] = (
                    f"C# method {method_name!r} corresponding to "
                    f"the meta-model method {method.name!r}")

    elif isinstance(intermediate_symbol, intermediate.Enumeration):
        pass
    else:
        assert_never(intermediate_symbol)

    if len(errors) > 0:
        errors.append(
            Error(
                intermediate_symbol.parsed.node,
                f"Naming collision(s) in C# code "
                f"for the symbol {intermediate_symbol.name!r}",
                underlying=errors))

    return None


class VerifiedIntermediateSymbolTable(intermediate.SymbolTable):
    """Represent a verified symbol table which can be used for code generation."""

    def __new__(
            cls, intermediate_symbol_table: intermediate.SymbolTable
    ) -> 'VerifiedIntermediateSymbolTable':
        raise AssertionError("Only for type annotation")


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def verify(
        intermediate_symbol_table: intermediate.SymbolTable,
        spec_impls: specific_implementations.SpecificImplementations
) -> Tuple[Optional[VerifiedIntermediateSymbolTable], Optional[List[Error]]]:
    """Verify that C# code can be generated from the ``intermediate_symbol_table``."""
    errors = []  # type: List[Error]

    structure_name_collisions = _verify_structure_name_collisions(
        intermediate_symbol_table=intermediate_symbol_table)

    errors.extend(structure_name_collisions)

    for symbol in intermediate_symbol_table.symbols:
        error = _verify_intra_structure_collisions(intermediate_symbol=symbol)
        if error is not None:
            errors.append(error)

    errors.extend(
        specific_implementations.verify_that_available_for_all_symbols(
            intermediate_symbol_table=intermediate_symbol_table,
            spec_impls=spec_impls))

    if len(errors) > 0:
        return None, errors

    return cast(VerifiedIntermediateSymbolTable, intermediate.SymbolTable), None


# endregion

# region Generation

def _description_paragraph_as_text(
        paragraph: docutils.nodes.paragraph
) -> Tuple[Optional[Stripped], Optional[str]]:
    """
    Render the body of a description paragraph as documentation XML.

    :param paragraph: to be rendered
    :return: the generated code, or error if the paragraph could not be translated
    """
    for child in paragraph.children:
        print(f"type(child) is {type(child)!r}")  # TODO: debug
        print(f"child is {child!r}")  # TODO: debug

    # TODO: test
    if len(paragraph.children) != 1:
        return (
            None,
            f"Expected a paragraph of a docstring to have a single child "
            f"(a docutils text), but got: {paragraph}")

    # TODO: test
    if not isinstance(paragraph.children[0], docutils.nodes.Text):
        return (
            None,
            f"Expected a paragraph of a docstring to consist only of text, "
            f"but got: {paragraph}")

    return paragraph.children[0].astext(), None


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _description_comment(
        description: intermediate.Description
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """Generate a documentation comment based on the docstring."""
    if len(description.document.children) == 0:
        return Stripped(""), None

    summary = None  # type: Optional[docutils.nodes.paragraph]
    remarks = None  # type: Optional[List[docutils.nodes.paragraph]]
    tail = []  # type: List[docutils.nodes.General]

    # Try to match the summary and the remarks
    if (
            len(description.document.children) >= 2
            and isinstance(description.document.children[0], docutils.nodes.paragraph)
            and isinstance(description.document.children[1], docutils.nodes.paragraph)
    ):
        summary = description.document.children[0]

        remarks = [description.document.children[1]]
        last_remark_index = 1
        for child in description.document.children[2:]:
            if isinstance(child, docutils.nodes.paragraph):
                remarks.append(child)
                last_remark_index += 1

        tail = description.document.children[last_remark_index + 1:]
    elif (
            len(description.document.children) >= 1
            and isinstance(description.document.children[0], docutils.nodes.paragraph)
    ):
        summary = description.document.children[0]
        tail = description.document.children[1:]
    else:
        tail = description.document.children

    # (2021-09-16, mristin)
    # We restrict ourselves here quite a lot. This function will need to evolve as
    # we add a larger variety of docstrings to the meta-model.
    #
    # For example, we need to translate ``:paramref:``'s to ``<paramref ...>`` in C#.
    # Additionally, we need to change the name of the argument accordingly (snake_case
    # to camelCase).

    # Blocks to be joined by a new-line
    blocks = []  # type: List[Stripped]

    if summary:
        summary_text, error = _description_paragraph_as_text(summary)
        if error:
            return None, Error(description.node, error)

        blocks.append(
            Stripped(
                f'<summary>\n'
                f'{xml.sax.saxutils.escape(summary_text)}\n'
                f'</summary>'))

    if remarks:
        remark_blocks = []  # type: List[Stripped]
        for remark in remarks:
            remark_text, error = _description_paragraph_as_text(remark)
            if error:
                return None, Error(description.node, error)

            remark_blocks.append(remark_text)

        assert len(remark_blocks) >= 1, \
            f"Expected at least one remark block since ``remarks`` defined: {remarks}"

        if len(remark_blocks) == 1:
            blocks.append(
                Stripped(
                    f'<remarks>\n'
                    f'{xml.sax.saxutils.escape(remark_blocks[0])}\n'
                    f'</remarks>'))
        else:
            remarks_paras = '\n'.join(
                f'<para>{xml.sax.saxutils.escape(remark_block)}</para>'
                for remark_block in remark_blocks)

            blocks.append(
                Stripped(
                    f'<remarks>\n'
                    f'{remarks_paras}\n'
                    f'</remarks>'))

    for tail_element in tail:
        # TODO: test
        if not isinstance(tail_element, docutils.nodes.field_list):
            return (
                None,
                Error(
                    description.node,
                    f"Expected only a field list to follow the summary and remarks, "
                    f"but got: {tail_element}"))

        for field in tail_element.children:
            assert len(field.children) == 2
            field_name, field_body = field.children
            assert isinstance(field_name, docutils.nodes.field_name)
            assert isinstance(field_body, docutils.nodes.field_body)

            # region Generate field body

            body_blocks = []  # type: List[Stripped]
            for body_child in field_body.children:
                if isinstance(body_child, docutils.nodes.paragraph):
                    body_block, error = _description_paragraph_as_text(body_child)
                    if error:
                        return None, Error(description.node, error)

                    body_blocks.append(body_block)
                else:
                    return (
                        None,
                        Error(
                            description.node,
                            f"Unhandled child of a field with name {field_name} "
                            f"and body: {field_body}"))

            if len(body_blocks) == 0:
                body = ''
            elif len(body_blocks) == 1:
                body = xml.sax.saxutils.escape(body_blocks[0])
            else:
                body = '\n'.join(
                    f'<para>{xml.sax.saxutils.escape(body_block)}</para>'
                    for body_block in body_blocks)

            # endregion

            # region Generate tags in the description

            assert (
                    len(field_name.children) == 1
                    and isinstance(field_name.children[0], docutils.nodes.Text)
            )

            name = field_name.children[0].astext()
            name_parts = name.split()
            if len(name_parts) > 2:
                # TODO: test
                return (
                    None,
                    Error(
                        description.node,
                        f"Expected one or two parts in a field name, "
                        f"but got: {field_name}"))

            if len(name_parts) == 1:
                directive = name_parts[0]
                if directive in ('return', 'returns'):
                    body_indented = textwrap.indent(body, csharp_common.INDENT)
                    blocks.append(Stripped(f'<returns>\n{body_indented}\n</returns>'))
                else:
                    return (
                        None,
                        Error(description.node, f"Unhandled directive: {directive}"))
            elif len(name_parts) == 2:
                directive, directive_arg = name_parts

                if directive == 'param':
                    arg_name = csharp_naming.argument_name(directive_arg)

                    if body != "":
                        indented_body = textwrap.indent(body, csharp_common.INDENT)
                        blocks.append(
                            Stripped(
                                f'<param name={xml.sax.saxutils.quoteattr(arg_name)}>\n'
                                f'{indented_body}\n'
                                f'</param>'))
                    else:
                        blocks.append(
                            Stripped(
                                f'<param name={xml.sax.saxutils.quoteattr(arg_name)}>'
                                f'</param>'))
                else:
                    return (
                        None,
                        Error(description.node, f"Unhandled directive: {directive}"))
            else:
                return (
                    None,
                    Error(description.node,
                          f"Expected one or two parts in a field name, "
                          f"but got: {field_name}"))

            # endregion

    # fmt: off
    text = Stripped(
        '\n'.join(
            f'/// {line}'
            for line in '\n'.join(blocks).splitlines()
        ))
    # fmt: on
    return text, None


@require(lambda symbol: not symbol.is_implementation_specific)
@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_enum(
        symbol: intermediate.Enumeration
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """Generate the C# code for the enum."""
    writer = io.StringIO()

    if symbol.description is not None:
        comment, error = _description_comment(symbol.description)
        if error:
            return None, error

        writer.write(comment)
        writer.write('\n')

    name = csharp_naming.enum_name(symbol.name)
    if len(symbol.literals) == 0:
        writer.write(f"public enum {name}\n{{\n}}")
        return Stripped(writer.getvalue()), None

    writer.write(f"public enum {name}\n{{")
    for i, literal in enumerate(symbol.literals):
        if i > 0:
            writer.write(",\n\n")

        if literal.description:
            literal_comment, error = _description_comment(literal.description)
            if error:
                return None, error

            writer.write(textwrap.indent(literal_comment, csharp_common.INDENT))
            writer.write('\n')

        writer.write(
            textwrap.indent(
                f'[EnumMember(Value = {csharp_common.string_literal(literal.value)})]\n'
                f'{csharp_naming.enum_literal_name(literal.name)}',
                csharp_common.INDENT))

    writer.write("\n}}")

    return Stripped(writer.getvalue()), None


@require(lambda symbol: not symbol.is_implementation_specific)
@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_interface(
        symbol: intermediate.Interface
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """Generate C# code for the given interface."""
    writer = io.StringIO()

    if symbol.description is not None:
        comment, error = _description_comment(symbol.description)
        if error:
            return None, error

        writer.write(comment)
        writer.write("\n")

    name = csharp_naming.interface_name(symbol.name)

    if len(symbol.inheritances) == 0:
        writer.write(f"public interface {name}\n{{\n")
    elif len(symbol.inheritances) == 1:
        inheritance = csharp_naming.interface_name(symbol.inheritances[0])
        writer.write(f"public interface {name} : {inheritance}\n{{\n")
    else:
        writer.write(f"public class {name} :\n")
        for i, inheritance in enumerate(
                map(csharp_naming.interface_name, symbol.inheritances)):
            if i > 0:
                writer.write(",\n")

            writer.write(textwrap.indent(inheritance, csharp_common.INDENT * 2))

        writer.write("\n{{\n")

    # Code blocks separated by double newlines and indented once
    codes = []  # type: List[Stripped]

    # region Getters and setters

    for prop in symbol.properties:
        prop_type = csharp_common.generate_type(prop.type_annotation)
        prop_name = csharp_naming.property_name(prop.name)

        if prop.description is not None:
            prop_comment, error = _description_comment(prop.description)
            if error:
                return None, error

            codes.append(
                Stripped(f"{prop_comment}\n{prop_type} {prop_name} {{ get; set; }}"))
        else:
            codes.append(Stripped(f"{prop_type} {prop_type} {{ get; set; }}"))

    # endregion

    # region Methods

    for signature in symbol.signatures:
        signature_blocks = []  # type: List[Stripped]

        if signature.description is not None:
            signature_comment, error = _description_comment(signature.description)
            if error:
                return None, error

            signature_blocks.append(signature_comment)

        # fmt: off
        returns = (
            csharp_common.generate_type(signature.returns)
            if signature.returns is not None else "void"
        )
        # fmt: on

        arg_codes = []  # type: List[Stripped]
        for arg in signature.arguments:
            arg_type = csharp_common.generate_type(arg.type_annotation)
            arg_name = csharp_naming.argument_name(arg.name)
            arg_codes.append(Stripped(f'{arg_type} {arg_name}'))

        signature_name = csharp_naming.method_name(signature.name)
        if len(arg_codes) > 2:
            arg_block = ",\n".join(arg_codes)
            arg_block_indented = textwrap.indent(arg_block, csharp_common.INDENT)
            signature_blocks.append(
                Stripped(f"{returns} {signature_name}(\n{arg_block_indented});"))
        elif len(arg_codes) == 1:
            signature_blocks.append(
                Stripped(f"{returns} {signature_name}({arg_codes[0]});"))
        else:
            assert len(arg_codes) == 0
            signature_blocks.append(Stripped(f"{returns} {signature_name}();"))

        codes.append(Stripped("\n".join(signature_blocks)))

    # endregion

    for i, code in enumerate(codes):
        if i > 0:
            writer.write("\n\n")

        writer.write(textwrap.indent(code, csharp_common.INDENT))
    writer.write("\n\n".join(codes))
    writer.write("\n}}")

    return Stripped(writer.getvalue()), None


@require(lambda symbol: not symbol.is_implementation_specific)
@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_class(
        symbol: intermediate.Class,
        spec_impls: specific_implementations.SpecificImplementations
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """Generate C# code for the given class."""
    writer = io.StringIO()

    if symbol.description is not None:
        comment, error = _description_comment(symbol.description)
        if error:
            return None, error

        writer.write(comment)
        writer.write("\n")

    name = csharp_naming.class_name(symbol.name)

    if len(symbol.interfaces) == 0:
        writer.write(f"public class {name}\n{{\n")
    elif len(symbol.interfaces) == 1:
        interface_name = csharp_naming.interface_name(symbol.interfaces[0])
        writer.write(f"public class {name} : {interface_name}\n{{\n")
    else:
        writer.write(f"public class {name} :\n")
        for i, interface_name in enumerate(
                map(csharp_naming.interface_name, symbol.interfaces)):
            if i > 0:
                writer.write(",\n")

            writer.write(textwrap.indent(interface_name, csharp_common.INDENT * 2))

        writer.write("\n{{\n")

    # Code blocks separated by double newlines and indented once
    codes = []  # type: List[Stripped]

    # region Getters and setters

    for prop in symbol.properties:
        prop_type = csharp_common.generate_type(prop.type_annotation)
        prop_name = csharp_naming.property_name(prop.name)

        prop_blocks = []  # type: List[Stripped]

        if prop.description is not None:
            prop_comment, error = _description_comment(prop.description)
            if error:
                return None, error

            prop_blocks.append(prop_comment)

        prop_blocks.append(Stripped(f"{prop_type} {prop_name} {{ get; set; }}"))

        codes.append(Stripped('\n'.join(prop_blocks)))

    # endregion

    # region Methods

    for method in symbol.methods:
        if method.is_implementation_specific:
            code = spec_impls[
                specific_implementations.ImplementationKey(
                    f"{symbol.name}/{method.name}")]

            codes.append(code)
        else:
            # (mristin, 2021-09-16):
            # At the moment, we do not transpile the method body and its contracts.
            # We want to finish the meta-model for the V3 and fix de/serialization
            # before taking on this rather hard task.

            return (
                None,
                Error(
                    symbol.parsed.node,
                    "At the moment, we do not transpile the method body and "
                    "its contracts."))

    # endregion

    # region Constructor

    if symbol.constructor.is_implementation_specific:
        code = spec_impls[
            specific_implementations.ImplementationKey(
                f"{symbol.name}/__init__")]

        codes.append(code)
    else:
        constructor_blocks = []  # type: List[Stripped]

        arg_codes = []  # type: List[Stripped]
        for arg in symbol.constructor.arguments:
            arg_type = csharp_common.generate_type(arg.type_annotation)
            arg_name = csharp_naming.argument_name(arg.name)
            arg_codes.append(Stripped(f'{arg_type} {arg_name}'))

        if len(arg_codes) == 0:
            return (
                None,
                Error(
                    symbol.parsed.node,
                    "An empty constructor is automatically generated, "
                    "which conflicts with the empty constructor "
                    "specified in the meta-model"))
        elif len(arg_codes) == 1:
            constructor_blocks.append(
                Stripped(f"{name}({arg_codes[0]})\n{{"))
        else:
            arg_block = ",\n".join(arg_codes)
            arg_block_indented = textwrap.indent(arg_block, csharp_common.INDENT)
            constructor_blocks.append(
                Stripped(f"{name}(\n{arg_block_indented})\n{{"))

        # TODO: continue here
        # TODO: transpile the constructor body here

        constructor_blocks.append("}}")

        codes.append(Stripped("\n".join(constructor_blocks)))

    # endregion

    for i, code in enumerate(codes):
        if i > 0:
            writer.write("\n\n")

        writer.write(textwrap.indent(code, csharp_common.INDENT))
    writer.write("\n\n".join(codes))
    writer.write("\n}}")

    return Stripped(writer.getvalue()), None


# fmt: off
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
@ensure(
    lambda result:
    not (result[0] is not None) or result.endswith('\n'),
    "Trailing newline mandatory for valid end-of-files"
)
# fmt: on
def generate(
        intermediate_symbol_table: VerifiedIntermediateSymbolTable,
        namespace: Identifier,
        spec_impls: specific_implementations.SpecificImplementations
) -> Tuple[Optional[str], Optional[List[Error]]]:
    """
    Generate the C# code of the structures based on the symbol table.

    The ``namespace`` defines the C# namespace.
    """
    warning = Stripped(textwrap.dedent("""\
        /*
         * This code has been automatically generated by aas-core-csharp-codegen.
         * Do NOT edit or append.
         */"""))

    blocks = [warning]  # type: List[Rstripped]

    using_directives = [
        "using EnumMemberAttribute = System.Runtime.Serialization.EnumMemberAttribute;",
        ("using JsonPropertyNameAttribute = "
         "System.Text.Json.Serialization.JsonPropertyNameAttribute;"),
        "using System.Collections.Generic;  // can't alias"
    ]  # type: List[str]

    if len(using_directives) > 0:
        blocks.append(Stripped("\n".join(using_directives)))

    blocks.append(Stripped(f"namespace {namespace}\n{{"))

    errors = []  # type: List[Error]

    for intermediate_symbol in intermediate_symbol_table.symbols:
        code = None  # type: Optional[Stripped]
        error = None  # type: Optional[Error]

        if intermediate_symbol.is_implementation_specific:
            # TODO: test
            code = spec_impls[
                specific_implementations.ImplementationKey(
                    intermediate_symbol.name)]
        else:
            if isinstance(intermediate_symbol, intermediate.Enumeration):
                # TODO: test
                code, error = _generate_enum(symbol=intermediate_symbol)
            elif isinstance(intermediate_symbol, intermediate.Interface):
                # TODO: test
                code, error = _generate_interface(
                    intermediate_symbol=intermediate_symbol)

            elif isinstance(intermediate_symbol, intermediate.Class):
                # TODO: impl
                code, error = _generate_class(
                    intermediate_symbol=intermediate_symbol,
                    spec_impls=spec_impls)
            else:
                assert_never(intermediate_symbol)

        assert (code is None) ^ (error is None)
        if error is not None:
            errors.append(error)
        else:
            assert code is not None
            blocks.append(Rstripped(textwrap.indent(code, '    ')))

    if len(errors) > 0:
        return None, errors

    blocks.append(Rstripped(f"}}  // namespace {namespace}"))

    blocks.append(warning)

    return '\n\n'.join(blocks), None

# endregion

# TODO: implement live_test 🠒 use C# compiler to actually create and compile the code!
