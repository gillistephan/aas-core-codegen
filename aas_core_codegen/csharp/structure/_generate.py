"""Generate the C# data structures from the intermediate representation."""
import io
import textwrap
import xml.sax.saxutils
from typing import Optional, Dict, List, Tuple, cast, Union, Sequence, Mapping, Final

import docutils.nodes
import docutils.parsers.rst.roles
import docutils.utils
from icontract import ensure, require

from aas_core_codegen import intermediate
from aas_core_codegen.intermediate import (
    construction as intermediate_construction,
    rendering as intermediate_rendering,
)

from aas_core_codegen import specific_implementations
from aas_core_codegen.common import Error, Identifier, assert_never, Stripped, Rstripped
from aas_core_codegen.csharp import (
    common as csharp_common,
    naming as csharp_naming,
    unrolling as csharp_unrolling,
)
from aas_core_codegen.csharp.common import INDENT as I, INDENT2 as II


# region Checks


def _verify_structure_name_collisions(
        symbol_table: intermediate.SymbolTable,
) -> List[Error]:
    """Verify that the C# names of the structures do not collide."""
    observed_structure_names = {}  # type: Dict[Identifier, intermediate.Symbol]

    errors = []  # type: List[Error]

    for symbol in symbol_table.symbols:
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
            # TODO-BEFORE-RELEASE (mristin, 2021-12-13): test
            errors.append(
                Error(
                    symbol.parsed.node,
                    f"The C# name {name!r} "
                    f"of the meta-model symbol {symbol.name!r} collides "
                    f"with another meta-model symbol "
                    f"{observed_structure_names[name].name!r}",
                )
            )
        else:
            observed_structure_names[name] = symbol

    # region Intra-structure collisions

    for symbol in symbol_table.symbols:
        collision_error = _verify_intra_structure_collisions(intermediate_symbol=symbol)

        if collision_error is not None:
            errors.append(collision_error)

    return errors


def _verify_intra_structure_collisions(
        intermediate_symbol: intermediate.Symbol,
) -> Optional[Error]:
    """Verify that no member names collide in the C# structure of the given symbol."""
    errors = []  # type: List[Error]

    if isinstance(intermediate_symbol, intermediate.Interface):
        observed_member_names = {}  # type: Dict[Identifier, str]

        for prop in intermediate_symbol.properties:
            prop_name = csharp_naming.property_name(prop.name)
            if prop_name in observed_member_names:
                # TODO-BEFORE-RELEASE (mristin, 2021-12-13): test
                errors.append(
                    Error(
                        prop.parsed.node,
                        f"C# property {prop_name!r} corresponding "
                        f"to the meta-model property {prop.name!r} collides with "
                        f"the {observed_member_names[prop_name]}",
                    )
                )
            else:
                observed_member_names[prop_name] = (
                    f"C# property {prop_name!r} corresponding to "
                    f"the meta-model property {prop.name!r}"
                )

        for signature in intermediate_symbol.signatures:
            method_name = csharp_naming.method_name(signature.name)

            if method_name in observed_member_names:
                # TODO-BEFORE-RELEASE (mristin, 2021-12-13): test
                errors.append(
                    Error(
                        signature.parsed.node,
                        f"C# method {method_name!r} corresponding "
                        f"to the meta-model method {signature.name!r} collides with "
                        f"the {observed_member_names[method_name]}",
                    )
                )
            else:
                observed_member_names[method_name] = (
                    f"C# method {method_name!r} corresponding to "
                    f"the meta-model method {signature.name!r}"
                )

    elif isinstance(intermediate_symbol, intermediate.Class):
        observed_member_names = {}  # type: Dict[Identifier, str]

        for prop in intermediate_symbol.properties:
            prop_name = csharp_naming.property_name(prop.name)
            if prop_name in observed_member_names:
                # TODO-BEFORE-RELEASE (mristin, 2021-12-13): test
                errors.append(
                    Error(
                        prop.parsed.node,
                        f"C# property {prop_name!r} corresponding "
                        f"to the meta-model property {prop.name!r} collides with "
                        f"the {observed_member_names[prop_name]}",
                    )
                )
            else:
                observed_member_names[prop_name] = (
                    f"C# property {prop_name!r} corresponding to "
                    f"the meta-model property {prop.name!r}"
                )

        methods_or_signatures = (
            []
        )  # type: Sequence[Union[intermediate.Method, intermediate.Signature]]

        if isinstance(intermediate_symbol, intermediate.Class):
            methods_or_signatures = intermediate_symbol.methods
        elif isinstance(intermediate_symbol, intermediate.Interface):
            methods_or_signatures = intermediate_symbol.signatures
        else:
            assert_never(intermediate_symbol)

        for signature in methods_or_signatures:
            method_name = csharp_naming.method_name(signature.name)

            if method_name in observed_member_names:
                # TODO-BEFORE-RELEASE (mristin, 2021-12-13): test
                errors.append(
                    Error(
                        signature.parsed.node,
                        f"C# method {method_name!r} corresponding "
                        f"to the meta-model method {signature.name!r} collides with "
                        f"the {observed_member_names[method_name]}",
                    )
                )
            else:
                observed_member_names[method_name] = (
                    f"C# method {method_name!r} corresponding to "
                    f"the meta-model method {signature.name!r}"
                )

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
                underlying=errors,
            )
        )

    return None


class VerifiedIntermediateSymbolTable(intermediate.SymbolTable):
    """Represent a verified symbol table which can be used for code generation."""

    # noinspection PyInitNewSignature
    def __new__(
            cls, symbol_table: intermediate.SymbolTable
    ) -> "VerifiedIntermediateSymbolTable":
        raise AssertionError("Only for type annotation")


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def verify(
        symbol_table: intermediate.SymbolTable,
) -> Tuple[Optional[VerifiedIntermediateSymbolTable], Optional[List[Error]]]:
    """Verify that C# code can be generated from the ``symbol_table``."""
    errors = []  # type: List[Error]

    structure_name_collisions = _verify_structure_name_collisions(
        symbol_table=symbol_table
    )

    errors.extend(structure_name_collisions)

    for symbol in symbol_table.symbols:
        error = _verify_intra_structure_collisions(intermediate_symbol=symbol)
        if error is not None:
            errors.append(error)

    if len(errors) > 0:
        return None, errors

    return cast(VerifiedIntermediateSymbolTable, symbol_table), None


# endregion

# region Generation


class _DescriptionElementRenderer(
    intermediate_rendering.DocutilsElementTransformer[str]
):
    """Render descriptions as C# docstring XML."""

    def transform_text(
            self, element: docutils.nodes.Text
    ) -> Tuple[Optional[str], Optional[str]]:
        return xml.sax.saxutils.escape(element.astext()), None

    def transform_symbol_reference_in_doc(
            self, element: intermediate.SymbolReferenceInDoc
    ) -> Tuple[Optional[str], Optional[str]]:
        name = None  # type: Optional[str]
        if isinstance(element.symbol, intermediate.Enumeration):
            name = csharp_naming.enum_name(element.symbol.name)
        elif isinstance(element.symbol, intermediate.Interface):
            name = csharp_naming.interface_name(element.symbol.name)
        elif isinstance(element.symbol, intermediate.Class):
            name = csharp_naming.class_name(element.symbol.name)
        else:
            assert_never(element.symbol)

        assert name is not None
        return f"<see cref={xml.sax.saxutils.quoteattr(name)} />", None

    def transform_attribute_reference_in_doc(
            self, element: intermediate.AttributeReferenceInDoc
    ) -> Tuple[Optional[str], Optional[str]]:
        cref = None  # type: Optional[str]

        if isinstance(element.reference, intermediate.PropertyReferenceInDoc):
            symbol_name = None  # type: Optional[str]

            if isinstance(element.reference.symbol, intermediate.Class):
                symbol_name = csharp_naming.class_name(element.reference.symbol.name)
            elif isinstance(element.reference.symbol, intermediate.Interface):
                symbol_name = csharp_naming.class_name(element.reference.symbol.name)
            else:
                assert_never(element.reference.symbol)

            prop_name = csharp_naming.property_name(element.reference.prop.name)

            assert symbol_name is not None
            cref = f"{symbol_name}.{prop_name}"
        elif isinstance(
                element.reference, intermediate.EnumerationLiteralReferenceInDoc):
            symbol_name = csharp_naming.enum_name(element.reference.symbol.name)
            literal_name = csharp_naming.enum_literal_name(
                element.reference.literal.name)

            cref = f"{symbol_name}.{literal_name}"
        else:
            assert_never(element.reference)

        assert cref is not None
        return f"<see cref={xml.sax.saxutils.quoteattr(cref)} />", None

    def transform_literal(
            self, element: docutils.nodes.literal
    ) -> Tuple[Optional[str], Optional[str]]:
        return f"<c>{xml.sax.saxutils.escape(element.astext())}</c>", None

    def transform_paragraph(
            self, element: docutils.nodes.paragraph
    ) -> Tuple[Optional[str], Optional[str]]:
        parts = []  # type: List[str]
        for child in element.children:
            text, error = self.transform(child)
            if error is not None:
                return None, error

            assert text is not None
            parts.append(text)

        return "".join(parts), None

    def transform_emphasis(
            self, element: docutils.nodes.emphasis
    ) -> Tuple[Optional[str], Optional[str]]:
        parts = []  # type: List[str]
        for child in element.children:
            text, error = self.transform(child)
            if error is not None:
                return None, error

            assert text is not None
            parts.append(text)

        return "<em>{}</em>".format("".join(parts)), None

    def transform_list_item(
            self, element: docutils.nodes.list_item
    ) -> Tuple[Optional[str], Optional[str]]:
        parts = []  # type: List[str]
        for child in element.children:
            text, error = self.transform(child)
            if error is not None:
                return None, error

            assert text is not None
            parts.append(text)

        return "<li>{}</li>".format("".join(parts)), None

    def transform_bullet_list(
            self, element: docutils.nodes.bullet_list
    ) -> Tuple[Optional[str], Optional[str]]:
        parts = ["<ul>\n"]
        for child in element.children:
            text, error = self.transform(child)
            if error is not None:
                return None, error

            assert text is not None
            parts.append(f"{text}\n")
        parts.append("</ul>")

        return "".join(parts), None

    def transform_note(
            self, element: docutils.nodes.note
    ) -> Tuple[Optional[str], Optional[str]]:
        parts = []  # type: List[str]
        for child in element.children:
            text, error = self.transform(child)
            if error is not None:
                return None, error

            assert text is not None
            parts.append(text)

        return "".join(parts), None

    def transform_reference(
            self, element: docutils.nodes.reference
    ) -> Tuple[Optional[str], Optional[str]]:
        parts = []  # type: List[str]
        for child in element.children:
            text, error = self.transform(child)
            if error is not None:
                return None, error

            assert text is not None
            parts.append(text)

        return "".join(parts), None

    def transform_document(
            self, element: docutils.nodes.document
    ) -> Tuple[Optional[str], Optional[str]]:
        if len(element.children) == 0:
            return "", None

        summary = None  # type: Optional[docutils.nodes.paragraph]
        remarks = []  # type: Optional[List[docutils.nodes.Element]]
        tail = []  # type: List[docutils.nodes.Element]

        # Try to match the summary and the remarks
        if len(element.children) >= 1:
            if not isinstance(element.children[0], docutils.nodes.paragraph):
                return None, (
                    f"Expected the first document element to be a summary and "
                    f"thus a paragraph, but got: {element.children[0]}"
                )

            summary = element.children[0]

        remainder = element.children[1:]
        for i, child in enumerate(remainder):
            if isinstance(
                    child,
                    (docutils.nodes.paragraph,
                     docutils.nodes.bullet_list,
                     docutils.nodes.note)):
                remarks.append(child)
            else:
                tail = remainder[i:]
                break

        # NOTE (2021-09-16, mristin):
        # We restrict ourselves here quite a lot. This function will need to evolve as
        # we add a larger variety of docstrings to the meta-model.
        #
        # For example, we need to translate ``:paramref:``'s to ``<paramref ...>`` in
        # C#. Additionally, we need to change the name of the argument accordingly
        # (``snake_case`` to ``camelCase``).

        # Blocks to be joined by a new-line
        blocks = []  # type: List[Stripped]

        renderer = _DescriptionElementRenderer()

        if summary:
            summary_text, error = renderer.transform(element=summary)
            if error:
                return None, error

            assert summary_text is not None
            blocks.append(Stripped(f"<summary>\n" f"{summary_text}\n" f"</summary>"))

        if remarks:
            remark_blocks = []  # type: List[str]
            for remark in remarks:
                remark_text, error = renderer.transform(element=remark)
                if error:
                    return None, error

                assert remark_text is not None
                remark_blocks.append(remark_text)

            assert len(remark_blocks) >= 1, (
                f"Expected at least one remark block "
                f"since ``remarks`` defined: {remarks}"
            )

            if len(remark_blocks) == 1:
                blocks.append(
                    Stripped(f"<remarks>\n" f"{remark_blocks[0]}\n" f"</remarks>")
                )
            else:
                remarks_paras = "\n".join(
                    f"<para>{remark_block}</para>" for remark_block in remark_blocks
                )

                blocks.append(
                    Stripped(f"<remarks>\n" f"{remarks_paras}\n" f"</remarks>")
                )

        for tail_element in tail:
            # TODO-BEFORE-RELEASE (mristin, 2021-12-13): test
            if not isinstance(tail_element, docutils.nodes.field_list):
                return None, (
                    f"Expected only a field list to follow the summary and remarks, "
                    f"but got: {tail_element}"
                )

            for field in tail_element.children:
                assert len(field.children) == 2
                field_name, field_body = field.children
                assert isinstance(field_name, docutils.nodes.field_name)
                assert isinstance(field_body, docutils.nodes.field_body)

                # region Generate field body

                body_blocks = []  # type: List[str]
                for body_child in field_body.children:
                    body_block, error = renderer.transform(body_child)
                    if error:
                        return None, error

                    body_blocks.append(body_block)

                if len(body_blocks) == 0:
                    body = ""
                elif len(body_blocks) == 1:
                    body = body_blocks[0]
                else:
                    body = "\n".join(
                        f"<para>{body_block}</para>" for body_block in body_blocks
                    )

                # endregion

                # region Generate tags in the description

                assert len(field_name.children) == 1 and isinstance(
                    field_name.children[0], docutils.nodes.Text
                )

                name = field_name.children[0].astext()
                name_parts = name.split()
                if len(name_parts) > 2:
                    # TODO-BEFORE-RELEASE (mristin, 2021-12-13): test
                    return (
                        None,
                        f"Expected one or two parts in a field name, "
                        f"but got: {field_name}",
                    )

                if len(name_parts) == 1:
                    directive = name_parts[0]
                    if directive in ("return", "returns"):
                        body_indented = textwrap.indent(body, I)
                        blocks.append(
                            Stripped(f"<returns>\n{body_indented}\n</returns>")
                        )
                    else:
                        return None, f"Unhandled directive: {directive}"

                elif len(name_parts) == 2:
                    directive, directive_arg = name_parts

                    if directive == "param":
                        arg_name = csharp_naming.argument_name(directive_arg)

                        if body != "":
                            indented_body = textwrap.indent(body, I)
                            blocks.append(
                                Stripped(
                                    f"<param name={xml.sax.saxutils.quoteattr(arg_name)}>\n"
                                    f"{indented_body}\n"
                                    f"</param>"
                                )
                            )
                        else:
                            blocks.append(
                                Stripped(
                                    f"<param name={xml.sax.saxutils.quoteattr(arg_name)}>"
                                    f"</param>"
                                )
                            )
                    else:
                        return None, f"Unhandled directive: {directive}"
                else:
                    return (
                        None,
                        f"Expected one or two parts in a field name, "
                        f"but got: {field_name}",
                    )

                # endregion

        # fmt: off
        text = '\n'.join(
            f'/// {line}'
            for line in '\n'.join(blocks).splitlines()
        )
        # fmt: on
        return text, None


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _description_comment(
        description: intermediate.Description,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """Generate a documentation comment based on the docstring."""
    if len(description.document.children) == 0:
        return Stripped(""), None

    renderer = _DescriptionElementRenderer()
    text, error = renderer.transform(description.document)
    if error:
        return None, Error(description.node, error)

    assert text is not None
    return Stripped(text), None


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_enum(
        symbol: intermediate.Enumeration,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """Generate the C# code for the enum."""
    writer = io.StringIO()

    if symbol.description is not None:
        comment, error = _description_comment(symbol.description)
        if error:
            return None, error

        writer.write(comment)
        writer.write("\n")

    name = csharp_naming.enum_name(symbol.name)
    if len(symbol.literals) == 0:
        writer.write(f"public enum {name}\n{{\n}}")
        return Stripped(writer.getvalue()), None

    writer.write(f"public enum {name}\n{{\n")
    for i, literal in enumerate(symbol.literals):
        if i > 0:
            writer.write(",\n\n")

        if literal.description:
            literal_comment, error = _description_comment(literal.description)
            if error:
                return None, error

            writer.write(textwrap.indent(literal_comment, I))
            writer.write("\n")

        writer.write(
            textwrap.indent(
                f"[EnumMember(Value = {csharp_common.string_literal(literal.value)})]\n"
                f"{csharp_naming.enum_literal_name(literal.name)}",
                I,
            )
        )

    writer.write("\n}")

    return Stripped(writer.getvalue()), None


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_interface(
        symbol: intermediate.Interface,
        ref_association: intermediate.Symbol
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """
    Generate C# code for the given interface.

    The ``ref_association`` indicates which symbol to use for representing references
    within an AAS.
    """
    writer = io.StringIO()

    if symbol.description is not None:
        comment, error = _description_comment(symbol.description)
        if error:
            return None, error

        writer.write(comment)
        writer.write("\n")

    name = csharp_naming.interface_name(symbol.name)

    inheritances = [inheritance.name for inheritance in symbol.inheritances] + [
        Identifier("Class")
    ]

    assert len(inheritances) > 0
    if len(inheritances) == 1:
        inheritance = csharp_naming.interface_name(inheritances[0])
        writer.write(f"public interface {name} : {inheritance}\n{{\n")
    else:
        writer.write(f"public interface {name} :\n")
        for i, inheritance in enumerate(
                map(csharp_naming.interface_name, inheritances)
        ):
            if i > 0:
                writer.write(",\n")

            writer.write(textwrap.indent(inheritance, II))

        writer.write("\n{\n")

    # Code blocks separated by double newlines and indented once
    blocks = []  # type: List[Stripped]

    # region Getters and setters

    for prop in symbol.properties:
        prop_type = csharp_common.generate_type(
            type_annotation=prop.type_annotation,
            ref_association=ref_association)
        prop_name = csharp_naming.property_name(prop.name)

        if prop.description is not None:
            prop_comment, error = _description_comment(prop.description)
            if error:
                return None, error

            blocks.append(
                Stripped(
                    f"{prop_comment}\npublic {prop_type} {prop_name} {{ get; set; }}"
                )
            )
        else:
            blocks.append(Stripped(f"public {prop_type} {prop_name} {{ get; set; }}"))

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
            csharp_common.generate_type(
                type_annotation=signature.returns,
                ref_association=ref_association)
            if signature.returns is not None else "void"
        )
        # fmt: on

        arg_codes = []  # type: List[Stripped]
        for arg in signature.arguments:
            arg_type = csharp_common.generate_type(
                type_annotation=arg.type_annotation,
                ref_association=ref_association)
            arg_name = csharp_naming.argument_name(arg.name)
            arg_codes.append(Stripped(f"{arg_type} {arg_name}"))

        signature_name = csharp_naming.method_name(signature.name)
        if len(arg_codes) > 2:
            arg_block = ",\n".join(arg_codes)
            arg_block_indented = textwrap.indent(arg_block, I)
            signature_blocks.append(
                Stripped(f"public {returns} {signature_name}(\n{arg_block_indented});")
            )
        elif len(arg_codes) == 1:
            signature_blocks.append(
                Stripped(f"public {returns} {signature_name}({arg_codes[0]});")
            )
        else:
            assert len(arg_codes) == 0
            signature_blocks.append(Stripped(f"public {returns} {signature_name}();"))

        blocks.append(Stripped("\n".join(signature_blocks)))

    # endregion

    for i, code in enumerate(blocks):
        if i > 0:
            writer.write("\n\n")

        writer.write(textwrap.indent(code, I))

    writer.write("\n}")

    return Stripped(writer.getvalue()), None


class _DescendBodyUnroller(csharp_unrolling.Unroller):
    """Generate the code that unrolls descent into an element."""

    #: If set, generates the code with unrolled yields.
    #: Otherwise, we do not unroll recursively.
    _recurse: Final[bool]

    #: Pre-computed descendability map. A type is descendable if we should unroll it
    #: further.
    _descendability: Final[Mapping[intermediate.TypeAnnotation, bool]]

    #: Symbol to be used to represent references within an AAS
    _ref_association: Final[intermediate.Symbol]

    def __init__(
            self,
            recurse: bool,
            descendability: Mapping[intermediate.TypeAnnotation, bool],
            ref_association: intermediate.Symbol
    ) -> None:
        """Initialize with the given values."""
        self._recurse = recurse
        self._descendability = descendability
        self._ref_association = ref_association

    def _unroll_builtin_atomic_type_annotation(
            self,
            unrollee_expr: str,
            type_annotation: intermediate.BuiltinAtomicTypeAnnotation,
            path: List[str],
            item_level: int,
            key_value_level: int,
    ) -> List[csharp_unrolling.Node]:
        """Generate code for the given specific ``type_annotation``."""
        # We can not descend into a built-in atomic type.
        return []

    def _unroll_our_atomic_type_or_ref_annotation(
            self,
            unrollee_expr: str,
            type_annotation: Union[
                intermediate.OurAtomicTypeAnnotation,
                intermediate.RefTypeAnnotation
            ],
            path: List[str],
            item_level: int,
            key_value_level: int,
    ) -> List[csharp_unrolling.Node]:
        """
        Generate the code for both our atomic type annotations and references.

        We merged :py:method:`._unroll_our_atomic_type_annotation` and
        :py:method:`._unroll_ref_type_annotation` together since they differ in only
        which symbol is unrolled over.
        """
        symbol = None  # type: Optional[intermediate.Symbol]
        if isinstance(type_annotation, intermediate.OurAtomicTypeAnnotation):
            symbol = type_annotation.symbol
        elif isinstance(type_annotation, intermediate.RefTypeAnnotation):
            symbol = self._ref_association
        else:
            assert_never(type_annotation)

        assert symbol is not None

        if isinstance(symbol, intermediate.Enumeration):
            return []

        assert isinstance(symbol, (intermediate.Class, intermediate.Interface))

        result = [
            csharp_unrolling.Node(
                f"yield return {unrollee_expr};", children=[]
            )
        ]

        if self._recurse:
            if self._descendability[type_annotation]:
                recurse_var = csharp_unrolling.Unroller._loop_var_name(
                    level=item_level, suffix="Item")

                result.append(
                    csharp_unrolling.Node(
                        text=textwrap.dedent(
                            f"""\
                        // Recurse
                        foreach (var {recurse_var} in {unrollee_expr}.Descend())
                        {{
                            yield return {recurse_var};
                        }}"""
                        ),
                        children=[],
                    )
                )
            else:
                result.append(
                    csharp_unrolling.Node(
                        text="// Recursive descent ends here.", children=[]
                    )
                )

        return result

    def _unroll_our_atomic_type_annotation(
            self,
            unrollee_expr: str,
            type_annotation: intermediate.OurAtomicTypeAnnotation,
            path: List[str],
            item_level: int,
            key_value_level: int,
    ) -> List[csharp_unrolling.Node]:
        """Generate code for the given specific ``type_annotation``."""
        return self._unroll_our_atomic_type_or_ref_annotation(
            unrollee_expr=unrollee_expr,
            type_annotation=type_annotation,
            path=path,
            item_level=item_level,
            key_value_level=key_value_level
        )

    def _unroll_list_type_annotation(
            self,
            unrollee_expr: str,
            type_annotation: intermediate.ListTypeAnnotation,
            path: List[str],
            item_level: int,
            key_value_level: int,
    ) -> List[csharp_unrolling.Node]:
        """Generate code for the given specific ``type_annotation``."""
        item_var = csharp_unrolling.Unroller._loop_var_name(
            level=item_level, suffix="Item")

        children = self.unroll(
            unrollee_expr=item_var,
            type_annotation=type_annotation.items,
            path=[],  # Path is unused in this context
            item_level=item_level + 1,
            key_value_level=key_value_level
        )

        if len(children) == 0:
            return []

        node = csharp_unrolling.Node(
            text=f"foreach (var {item_var} in {unrollee_expr})",
            children=children,
        )

        return [node]

    def _unroll_optional_type_annotation(
            self,
            unrollee_expr: str,
            type_annotation: intermediate.OptionalTypeAnnotation,
            path: List[str],
            item_level: int,
            key_value_level: int,
    ) -> List[csharp_unrolling.Node]:
        """Generate code for the given specific ``type_annotation``."""
        children = self.unroll(
            unrollee_expr=unrollee_expr,
            type_annotation=type_annotation.value,
            path=path,
            item_level=item_level,
            key_value_level=key_value_level
        )

        if len(children) == 0:
            return []

        return [
            csharp_unrolling.Node(
                text=f"if ({unrollee_expr} != null)", children=children
            )
        ]

    def _unroll_ref_type_annotation(
            self,
            unrollee_expr: str,
            type_annotation: intermediate.RefTypeAnnotation,
            path: List[str],
            item_level: int,
            key_value_level: int,
    ) -> List[csharp_unrolling.Node]:
        """Generate code for the given specific ``type_annotation``."""
        return self._unroll_our_atomic_type_or_ref_annotation(
            unrollee_expr=unrollee_expr,
            type_annotation=type_annotation,
            path=path,
            item_level=item_level,
            key_value_level=key_value_level
        )


def _generate_descend_body(
        symbol: intermediate.Class,
        recurse: bool,
        ref_association: intermediate.Symbol
) -> Stripped:
    """
    Generate the body of the ``Descend`` and ``DescendOnce`` methods.

    With this function, we can unroll the recursion as a simple optimization
    in the recursive case.

    The ``ref_association`` indicates which symbol to use for representing references
    within an AAS.
    """
    blocks = []  # type: List[Stripped]

    for prop in symbol.properties:
        descendability = intermediate.map_descendability(
            type_annotation=prop.type_annotation,
            ref_association=ref_association
        )

        if not descendability[prop.type_annotation]:
            continue

        # region Unroll

        unroller = _DescendBodyUnroller(
            recurse=recurse,
            descendability=descendability,
            ref_association=ref_association
        )

        roots = unroller.unroll(
            unrollee_expr=csharp_naming.property_name(prop.name),
            type_annotation=prop.type_annotation,
            path=[],  # We do not use path in this context
            item_level=0,
            key_value_level=0
        )

        assert len(roots) > 0, (
            "Since the type annotation was descendable, we must have obtained "
            "at least one unrolling node"
        )

        blocks.extend(Stripped(csharp_unrolling.render(root)) for root in roots)

        # endregion

    if len(blocks) == 0:
        blocks.append(Stripped("// No descendable properties\nyield break;"))

    return Stripped("\n\n".join(blocks))


def _generate_descend_once_method(
        symbol: intermediate.Class,
        ref_association: intermediate.Symbol
) -> Stripped:
    """
    Generate the ``DescendOnce`` method for the class of the ``symbol``.

    The ``ref_association`` indicates which symbol to use for representing references
    within an AAS.
    """

    body = _generate_descend_body(
        symbol=symbol, recurse=False, ref_association=ref_association)

    indented_body = textwrap.indent(body, I)

    return Stripped(
        f"""\
/// <summary>
/// Iterate over all the class instances referenced from this instance 
/// without further recursion.
/// </summary>
public IEnumerable<IClass> DescendOnce()
{{
{indented_body}
}}"""
    )


def _generate_descend_method(
        symbol: intermediate.Class,
        ref_association: intermediate.Symbol
) -> Stripped:
    """
    Generate the recursive ``Descend`` method for the class of the ``symbol``.

    The ``ref_association`` indicates which symbol to use for representing references
    within an AAS.
    """

    body = _generate_descend_body(
        symbol=symbol, recurse=True, ref_association=ref_association)

    indented_body = textwrap.indent(body, I)

    return Stripped(
        f"""\
/// <summary>
/// Iterate recursively over all the class instances referenced from this instance.
/// </summary>
public IEnumerable<IClass> Descend()
{{
{indented_body}
}}"""
    )


def _generate_default_value(default: intermediate.Default) -> Stripped:
    """Generate the C# code representing the default value of an argument."""
    code = None  # type: Optional[str]

    if default is not None:
        if isinstance(default, intermediate.DefaultConstant):
            if default.value is None:
                code = "null"
            elif isinstance(default.value, bool):
                code = "true" if default.value else "false"
            elif isinstance(default.value, str):
                code = csharp_common.string_literal(default.value)
            elif isinstance(default.value, int):
                code = str(default.value)
            elif isinstance(default, float):
                code = f"{default}d"
            else:
                assert_never(default.value)
        elif isinstance(default, intermediate.DefaultEnumerationLiteral):
            code = ".".join(
                [
                    csharp_naming.enum_name(default.enumeration.name),
                    csharp_naming.enum_literal_name(default.literal.name),
                ]
            )
        else:
            assert_never(default)

    assert code is not None
    return Stripped(code)


@require(lambda symbol: not symbol.is_implementation_specific)
@require(lambda symbol: not symbol.constructor.is_implementation_specific)
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _generate_constructor(
        symbol: intermediate.Class,
        ref_association: intermediate.Symbol
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """
    Generate the constructor function for the given symbol.

    The ``ref_association`` indicates which symbol to use for representing references
    within an AAS.
    """
    cls_name = csharp_naming.class_name(symbol.name)

    blocks = []  # type: List[str]

    arg_codes = []  # type: List[str]
    for arg in symbol.constructor.arguments:
        arg_type = csharp_common.generate_type(
            type_annotation=arg.type_annotation,
            ref_association=ref_association)
        arg_name = csharp_naming.argument_name(arg.name)

        if arg.default is None:
            arg_codes.append(Stripped(f"{arg_type} {arg_name}"))
        else:
            arg_codes.append(
                Stripped(
                    f"{arg_type} {arg_name} = {_generate_default_value(arg.default)}"
                )
            )

    if len(arg_codes) == 0:
        return (
            None,
            Error(
                symbol.parsed.node,
                "An empty constructor is automatically generated, "
                "which conflicts with the empty constructor "
                "specified in the meta-model",
            ),
        )

    elif len(arg_codes) == 1:
        blocks.append(f"public {cls_name}({arg_codes[0]})\n{{")
    else:
        arg_block = ",\n".join(arg_codes)
        arg_block_indented = textwrap.indent(arg_block, I)
        blocks.append(Stripped(f"public {cls_name}(\n{arg_block_indented})\n{{"))

    body = []  # type: List[str]
    for stmt in symbol.constructor.statements:
        if isinstance(stmt, intermediate_construction.AssignArgument):
            if stmt.default is None:
                body.append(
                    f"{csharp_naming.property_name(stmt.name)} = "
                    f"{csharp_naming.argument_name(stmt.argument)};"
                )
            else:
                if isinstance(stmt.default, intermediate_construction.EmptyList):
                    prop = symbol.properties_by_name[stmt.name]
                    prop_type = csharp_common.generate_type(
                        type_annotation=prop.type_annotation,
                        ref_association=ref_association)

                    arg_name = csharp_naming.argument_name(stmt.argument)

                    # Write the assignment as a ternary operator
                    writer = io.StringIO()
                    writer.write(f"{csharp_naming.property_name(stmt.name)} = ")
                    writer.write(f"({arg_name} != null)\n")
                    writer.write(textwrap.indent(f"? {arg_name}\n", I))
                    writer.write(textwrap.indent(f": new {prop_type}();", I))

                    body.append(writer.getvalue())
                elif isinstance(
                        stmt.default, intermediate_construction.DefaultEnumLiteral
                ):
                    literal_code = ".".join(
                        [
                            csharp_naming.enum_name(stmt.default.enum.name),
                            csharp_naming.enum_literal_name(stmt.default.literal.name),
                        ]
                    )

                    body.append(
                        f"{csharp_naming.property_name(stmt.name)} = "
                        f"{literal_code};"
                    )
                else:
                    assert_never(stmt.default)

        else:
            assert_never(stmt)

    blocks.append("\n".join(textwrap.indent(stmt_code, I) for stmt_code in body))

    blocks.append("}")

    return Stripped("\n".join(blocks)), None


def _generate_default_value_for_type_annotation(
        type_annotation: intermediate.TypeAnnotation,
        ref_association: intermediate.Symbol
) -> Stripped:
    """
    Generate the C# code representing the default value for the given type.

    The ``ref_association`` indicates which symbol to use for representing references
    within an AAS.
    """
    code = None  # type: Optional[str]
    if isinstance(type_annotation, intermediate.BuiltinAtomicTypeAnnotation):
        if type_annotation.a_type == intermediate.BuiltinAtomicType.BOOL:
            code = "false"
        elif type_annotation.a_type == intermediate.BuiltinAtomicType.INT:
            code = "0"
        elif type_annotation.a_type == intermediate.BuiltinAtomicType.FLOAT:
            code = "0d"
        elif type_annotation.a_type == intermediate.BuiltinAtomicType.STR:
            code = '""'
        else:
            assert_never(type_annotation.a_type)
    elif isinstance(
            type_annotation,
            (intermediate.OurAtomicTypeAnnotation,
             intermediate.ListTypeAnnotation,
             intermediate.RefTypeAnnotation),
    ):
        csharp_type = csharp_common.generate_type(
            type_annotation=type_annotation,
            ref_association=ref_association)

        code = f"new {csharp_type}()"
    elif isinstance(type_annotation, intermediate.OptionalTypeAnnotation):
        code = "null"
    else:
        assert_never(type_annotation)

    assert code is not None
    return Stripped(code)


@require(lambda symbol: not symbol.is_implementation_specific)
@require(lambda symbol: not symbol.constructor.is_implementation_specific)
def _generate_default_constructor(
        symbol: intermediate.Class,
        ref_association: intermediate.Symbol
) -> Stripped:
    """
    Generate the default constructor for the given symbol.

    The constructor sets all the properties to their default values.

    The ``ref_association`` indicates which symbol to use for representing references
    within an AAS.
    """
    cls_name = csharp_naming.class_name(symbol.name)

    default_values = []  # type: List[Stripped]

    for arg in symbol.constructor.arguments:
        if arg.default is None:
            default_values.append(
                _generate_default_value_for_type_annotation(
                    type_annotation=arg.type_annotation,
                    ref_association=ref_association
                )
            )
        else:
            default_values.append(_generate_default_value(default=arg.default))

    writer = io.StringIO()

    assert len(default_values) >= 1, (
        "We are constructing the default constructor "
        "so we expected at least one default value, but got none."
    )

    if len(default_values) == 1:
        writer.write(f"public {cls_name}() : this({default_values[0]})\n")
    else:
        writer.write(f"public {cls_name}() : this(\n")
        for i, default_value in enumerate(default_values):
            writer.write(f"{I}{default_value}")

            if i < len(default_values) - 1:
                writer.write(",\n")
            else:
                writer.write(")\n")

    writer.write("{\n" f"{I}// Intentionally left empty.\n" "}")

    return Stripped(writer.getvalue())


@require(lambda symbol: not symbol.is_implementation_specific)
@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _generate_class(
        symbol: intermediate.Class,
        spec_impls: specific_implementations.SpecificImplementations,
        ref_association: intermediate.Symbol
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """
    Generate C# code for the given class.

    The ``ref_association`` indicates which symbol to use for representing references
    within an AAS.
    """
    writer = io.StringIO()

    if symbol.description is not None:
        comment, error = _description_comment(symbol.description)
        if error:
            return None, error

        writer.write(comment)
        writer.write("\n")

    name = csharp_naming.class_name(symbol.name)

    interfaces = [interface.name for interface in symbol.interfaces] + [
        Identifier("Class")
    ]

    assert len(interfaces) > 0
    if len(interfaces) == 1:
        interface_name = csharp_naming.interface_name(interfaces[0])
        writer.write(f"public class {name} : {interface_name}\n{{\n")
    else:
        writer.write(f"public class {name} :\n")
        for i, interface_name in enumerate(
                map(csharp_naming.interface_name, interfaces)
        ):
            if i > 0:
                writer.write(",\n")

            writer.write(textwrap.indent(interface_name, II))

        writer.write("\n{\n")

    # Code blocks separated by double newlines and indented once
    blocks = []  # type: List[Stripped]

    # region Getters and setters

    for prop in symbol.properties:
        prop_type = csharp_common.generate_type(
            type_annotation=prop.type_annotation,
            ref_association=ref_association)

        prop_name = csharp_naming.property_name(prop.name)

        prop_blocks = []  # type: List[Stripped]

        if prop.description is not None:
            prop_comment, error = _description_comment(prop.description)
            if error:
                return None, error

            prop_blocks.append(prop_comment)

        prop_blocks.append(Stripped(f"public {prop_type} {prop_name} {{ get; set; }}"))

        blocks.append(Stripped("\n".join(prop_blocks)))

    # endregion

    # region Methods

    errors = []  # type: List[Error]

    for method in symbol.methods:
        if method.is_implementation_specific:
            implementation_key = specific_implementations.ImplementationKey(
                f"{symbol.name}/{method.name}.cs"
            )

            implementation = spec_impls.get(implementation_key, None)

            if implementation is None:
                errors.append(
                    Error(
                        method.parsed.node,
                        f"The implementation is missing for the implementation-specific "
                        f"method: {implementation_key}",
                    )
                )
                continue

            blocks.append(implementation)
        else:
            # NOTE (mristin, 2021-09-16):
            # At the moment, we do not transpile the method body and its contracts.
            # We want to finish the meta-model for the V3 and fix de/serialization
            # before taking on this rather hard task.

            errors.append(
                Error(
                    symbol.parsed.node,
                    "At the moment, we do not transpile the method body and "
                    "its contracts.",
                )
            )

    blocks.append(
        _generate_descend_once_method(
            symbol=symbol, ref_association=ref_association))

    blocks.append(
        _generate_descend_method(
            symbol=symbol,
            ref_association=ref_association))

    blocks.append(
        Stripped(
            textwrap.dedent(
                f"""\
        /// <summary>
        /// Accept the <paramref name="visitor" /> to visit this instance 
        /// for double dispatch.
        /// </summary>
        public void Accept(Visitation.IVisitor visitor)
        {{
        {I}visitor.Visit(this);
        }}"""
            )
        )
    )

    blocks.append(
        Stripped(
            textwrap.dedent(
                f"""\
        /// <summary>
        /// Accept the visitor to visit this instance for double dispatch 
        /// with the <paramref name="context" />.
        /// </summary>
        public void Accept<C>(Visitation.IVisitorWithContext<C> visitor, C context)
        {{
        {I}visitor.Visit(this, context);
        }}"""
            )
        )
    )

    blocks.append(
        Stripped(
            textwrap.dedent(
                f"""\
        /// <summary>
        /// Accept the <paramref name="transformer" /> to transform this instance 
        /// for double dispatch.
        /// </summary>
        public T Transform<T>(Visitation.ITransformer<T> transformer)
        {{
        {I}return transformer.Transform(this);
        }}"""
            )
        )
    )

    blocks.append(
        Stripped(
            textwrap.dedent(
                f"""\
        /// <summary>
        /// Accept the <paramref name="transformer" /> to visit this instance 
        /// for double dispatch with the <paramref name="context" />.
        /// </summary>
        public T Transform<C, T>(
        {I}Visitation.ITransformerWithContext<C, T> transformer, C context)
        {{
        {I}return transformer.Transform(this, context);
        }}"""
            )
        )
    )

    # endregion

    # region Constructor

    if symbol.constructor.is_implementation_specific:
        implementation_key = specific_implementations.ImplementationKey(
            f"{symbol.name}/{symbol.name}.cs"
        )
        implementation = spec_impls.get(implementation_key, None)

        if implementation is None:
            errors.append(
                Error(
                    symbol.parsed.node,
                    f"The implementation of the implementation-specific constructor "
                    f"is missing: {implementation_key}",
                )
            )
        else:
            blocks.append(implementation)
    else:
        constructor_block, error = _generate_constructor(
            symbol=symbol, ref_association=ref_association)

        if error is not None:
            errors.append(error)
        else:
            blocks.append(constructor_block)

            if any(arg.default is None for arg in symbol.constructor.arguments):
                # We _generate_rdf the default constructor only if it has not been already
                # defined by specifying the default values for all the arguments.
                blocks.append(
                    _generate_default_constructor(
                        symbol=symbol,
                        ref_association=ref_association))

    # endregion

    if len(errors) > 0:
        return None, Error(
            symbol.parsed.node,
            f"Failed to generate the code for the class {symbol.name}",
            errors,
        )

    for i, code in enumerate(blocks):
        if i > 0:
            writer.write("\n\n")

        writer.write(textwrap.indent(code, I))

    writer.write("\n}")

    return Stripped(writer.getvalue()), None


# fmt: off
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
@ensure(
    lambda result:
    not (result[0] is not None) or result[0].endswith('\n'),
    "Trailing newline mandatory for valid end-of-files"
)
# fmt: on
def generate(
        symbol_table: VerifiedIntermediateSymbolTable,
        namespace: csharp_common.NamespaceIdentifier,
        spec_impls: specific_implementations.SpecificImplementations,
) -> Tuple[Optional[str], Optional[List[Error]]]:
    """
    Generate the C# code of the structures based on the symbol table.

    The ``namespace`` defines the AAS C# namespace.
    """
    blocks = [csharp_common.WARNING]  # type: List[Rstripped]

    using_directives = [
        "using EnumMemberAttribute = System.Runtime.Serialization.EnumMemberAttribute;",
        "using System.Collections.Generic;  // can't alias",
    ]  # type: List[str]

    if len(using_directives) > 0:
        blocks.append(Stripped("\n".join(using_directives)))

    blocks.append(Stripped(f"namespace {namespace}\n{{"))

    blocks.append(
        Rstripped(
            textwrap.indent(
                textwrap.dedent(
                    f"""\
        /// <summary>
        /// Represent a general class of an AAS model.
        /// </summary>
        public interface IClass
        {{
            /// <summary>
            /// Iterate over all the class instances referenced from this instance 
            /// without further recursion.
            /// </summary>
            public IEnumerable<IClass> DescendOnce();
            
            /// <summary>
            /// Iterate recursively over all the class instances referenced from this instance.
            /// </summary>
            public IEnumerable<IClass> Descend();

            /// <summary>
            /// Accept the <paramref name="visitor" /> to visit this instance 
            /// for double dispatch.
            /// </summary>
            public void Accept(Visitation.IVisitor visitor);
            
            /// <summary>
            /// Accept the visitor to visit this instance for double dispatch 
            /// with the <paramref name="context" />.
            /// </summary>
            public void Accept<C>(Visitation.IVisitorWithContext<C> visitor, C context);
            
            /// <summary>
            /// Accept the <paramref name="transformer" /> to transform this instance 
            /// for double dispatch.
            /// </summary>
            public T Transform<T>(Visitation.ITransformer<T> transformer);
            
            /// <summary>
            /// Accept the <paramref name="transformer" /> to visit this instance 
            /// for double dispatch with the <paramref name="context" />.
            /// </summary>
            public T Transform<C, T>(
            {I}Visitation.ITransformerWithContext<C, T> transformer, C context);                        
        }}"""
                ),
                I,
            )
        )
    )

    errors = []  # type: List[Error]

    for intermediate_symbol in symbol_table.symbols:
        code = None  # type: Optional[Stripped]
        error = None  # type: Optional[Error]

        if (
                isinstance(intermediate_symbol, intermediate.Class)
                and intermediate_symbol.is_implementation_specific
        ):
            implementation_key = specific_implementations.ImplementationKey(
                f"{intermediate_symbol.name}.cs"
            )

            code = spec_impls.get(implementation_key, None)
            if code is None:
                error = Error(
                    intermediate_symbol.parsed.node,
                    f"The implementation is missing "
                    f"for the implementation-specific class: {implementation_key}",
                )
        else:
            if isinstance(intermediate_symbol, intermediate.Enumeration):
                # TODO-BEFORE-RELEASE (mristin, 2021-12-13): test
                code, error = _generate_enum(symbol=intermediate_symbol)
            elif isinstance(intermediate_symbol, intermediate.Interface):
                # TODO-BEFORE-RELEASE (mristin, 2021-12-13): test
                code, error = _generate_interface(
                    symbol=intermediate_symbol,
                    ref_association=symbol_table.ref_association)

            elif isinstance(intermediate_symbol, intermediate.Class):
                code, error = _generate_class(
                    symbol=intermediate_symbol, spec_impls=spec_impls,
                    ref_association=symbol_table.ref_association
                )
            else:
                assert_never(intermediate_symbol)

        assert (code is None) ^ (error is None)
        if error is not None:
            errors.append(error)
        else:
            assert code is not None
            blocks.append(Rstripped(textwrap.indent(code, "    ")))

    if len(errors) > 0:
        return None, errors

    blocks.append(Rstripped(f"}}  // namespace {namespace}"))

    blocks.append(csharp_common.WARNING)

    out = io.StringIO()
    for i, block in enumerate(blocks):
        if i > 0:
            out.write("\n\n")

        out.write(block)

    out.write("\n")

    return out.getvalue(), None

# endregion
