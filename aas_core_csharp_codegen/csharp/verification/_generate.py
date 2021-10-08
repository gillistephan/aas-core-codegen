"""Generate the invariant verifiers from the intermediate representation."""
import io
import textwrap
import xml.sax.saxutils
from typing import Tuple, Optional, List, Sequence

from icontract import ensure, require

from aas_core_csharp_codegen.csharp import (
    common as csharp_common,
    naming as csharp_naming,
    unrolling as csharp_unrolling
)
from aas_core_csharp_codegen import intermediate
from aas_core_csharp_codegen.common import Error, Stripped, Rstripped, assert_never, \
    Identifier
from aas_core_csharp_codegen.csharp import specific_implementations
from aas_core_csharp_codegen.specific_implementations import ImplementationKey


# region Verify

def verify(
        spec_impls: specific_implementations.SpecificImplementations
) -> Optional[List[str]]:
    """Verify all the implementation snippets related to verification."""
    errors = []  # type: List[str]

    expected_keys = [
        'Verification/is_IRI', 'Verification/is_IRDI', 'Verification/is_ID_short',
        'Verification/Error', 'Verification/Errors'
    ]
    for key in expected_keys:
        if ImplementationKey(key) not in spec_impls:
            errors.append(f"The implementation snippet is missing for: {key}")

    if len(errors) == 0:
        return None

    return errors


# endregion

# region Generate


def _generate_pattern_class(
        spec_impls: specific_implementations.SpecificImplementations
) -> Stripped:
    """Generate the Pattern class used for verifying different patterns."""
    blocks = [
        spec_impls[ImplementationKey('Verification/is_IRI')],
        spec_impls[ImplementationKey('Verification/is_IRDI')],
        spec_impls[ImplementationKey('Verification/is_ID_short')]
    ]  # type: List[str]

    writer = io.StringIO()
    writer.write('public static class Pattern\n{\n')
    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n\n')

        writer.write(textwrap.indent(block.strip(), csharp_common.INDENT))

    writer.write('\n}')
    return Stripped(writer.getvalue())


def _generate_enum_value_sets(symbol_table: intermediate.SymbolTable) -> Stripped:
    """Generate a class that pre-computes the sets of allowed enumeration literals."""
    blocks = []  # type: List[Stripped]

    for symbol in symbol_table.symbols:
        if not isinstance(symbol, intermediate.Enumeration):
            continue

        enum_name = csharp_naming.enum_name(symbol.name)
        blocks.append(Stripped(
            f"public static HashSet<int> For{enum_name} = new HashSet<int>(\n"
            f"{csharp_common.INDENT}System.Enum.GetValues(typeof({enum_name})).Cast<int>());"))

    writer = io.StringIO()
    writer.write(textwrap.dedent('''\
        /// <summary>
        /// Hash allowed enum values for efficient validation of enums.
        /// </summary> 
        private static class EnumValueSet
        {
        '''))
    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n\n')

        writer.write(textwrap.indent(block, csharp_common.INDENT))

    writer.write('\n}  // private static class EnumValueSet')

    return Stripped(writer.getvalue())


@require(lambda cls, prop: prop in cls.properties)
def _unroll_enumeration_check(
        cls: intermediate.Class,
        prop: intermediate.Property) -> Stripped:
    """Generate the code for unrolling the enumeration checks for the given property."""

    @require(lambda var_index: var_index >= 0)
    @require(lambda suffix: suffix in ("Item", "KeyValue"))
    def var_name(var_index: int, suffix: str) -> Identifier:
        """Generate the name of the loop variable."""
        if var_index == 0:
            if suffix == 'Item':
                return Identifier(f"an{suffix}")
            else:
                assert suffix == 'KeyValue'
                return Identifier(f"a{suffix}")

        elif var_index == 1:
            return Identifier(f"another{suffix}")
        else:
            return Identifier("yet" + "Yet" * (var_index - 1) + f"another{suffix}")

    prop_name = csharp_naming.property_name(prop.name)

    def unroll(
            current_var_name: str,
            item_count: int,
            key_value_count: int,
            path: List[str],
            type_anno: intermediate.TypeAnnotation
    ) -> List[csharp_unrolling.Node]:
        """Generate the node corresponding to the ``type_anno`` and recurse."""
        if isinstance(type_anno, intermediate.BuiltinAtomicTypeAnnotation):
            return []

        elif isinstance(type_anno, intermediate.OurAtomicTypeAnnotation):
            if not isinstance(type_anno.symbol, intermediate.Enumeration):
                return []

            enum_name = csharp_naming.enum_name(type_anno.symbol.name)
            joined_pth = '/'.join(path)

            return [
                csharp_unrolling.Node(
                    text=textwrap.dedent(f'''\
                    if (!EnumValueSet.For{enum_name}.Contains(
                    {csharp_common.INDENT2}(int){current_var_name}))
                    {{
                    {csharp_common.INDENT}errors.Add(
                    {csharp_common.INDENT2}new Error(
                    {csharp_common.INDENT3}$"{{path}}/{joined_pth}",
                    {csharp_common.INDENT3}$"Invalid {{nameof({enum_name})}}: {{{current_var_name}}}"));
                    }}'''),
                    children=[])]

        elif isinstance(type_anno, (
                intermediate.ListTypeAnnotation, intermediate.SequenceTypeAnnotation,
                intermediate.SetTypeAnnotation)):
            item_var = var_name(item_count, "Item")

            children = unroll(
                current_var_name=item_var,
                item_count=item_count + 1,
                key_value_count=key_value_count,
                path=path + [f'{{{item_var}}}'],
                type_anno=type_anno.items)

            if len(children) == 0:
                return []

            node = csharp_unrolling.Node(
                text=f"foreach (var {item_var} in {current_var_name}",
                children=children)

            return [node]

        elif isinstance(type_anno, (
                intermediate.MappingTypeAnnotation,
                intermediate.MutableMappingTypeAnnotation
        )):
            key_value_var = var_name(key_value_count + 1, "KeyValue")

            key_children = unroll(
                current_var_name=f'{key_value_var}.Key',
                item_count=item_count,
                key_value_count=key_value_count + 1,
                path=path + [f'{{{key_value_var}.Key}}'],
                type_anno=type_anno.keys)

            value_children = unroll(
                current_var_name=f'{key_value_var}.Value',
                item_count=item_count,
                key_value_count=key_value_count + 1,
                path=path + [f'{{{key_value_var}.Key}}'],
                type_anno=type_anno.values)

            children = key_children + value_children

            if len(children) > 0:
                return [csharp_unrolling.Node(
                    text=f'foreach (var {key_value_var} in {current_var_name})',
                    children=children)]
            else:
                return []

        elif isinstance(type_anno, intermediate.OptionalTypeAnnotation):
            children = unroll(
                current_var_name=current_var_name,
                item_count=item_count,
                key_value_count=key_value_count,
                path=path,
                type_anno=type_anno.value)
            if len(children) > 0:
                return [csharp_unrolling.Node(
                    text=f"if ({current_var_name} != null)", children=children)]
            else:
                return []
        else:
            assert_never(type_anno)

    arg_name = csharp_naming.argument_name(cls.name)

    roots = unroll(
        current_var_name=f'{arg_name}.{prop_name}',
        item_count=0,
        key_value_count=0,
        path=[prop_name],
        type_anno=prop.type_annotation)

    if len(roots) == 0:
        return Stripped('')

    blocks = [csharp_unrolling.render(root) for root in roots]
    return Stripped('\n\n'.join(blocks))


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _generate_implementation_verify(
        cls: intermediate.Class
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """Generate the verify function in the ``Implementation`` class."""
    blocks = []  # type: List[Stripped]

    cls_name = csharp_naming.class_name(cls.name)

    if len(cls.invariants) == 0:
        blocks.append(Stripped(f'// There are no invariants defined for {cls_name}.'))
    else:
        pass
        # TODO: transpile the invariants into body_blocks

    for prop in cls.properties:
        enum_check_block = _unroll_enumeration_check(cls=cls, prop=prop)
        if enum_check_block != '':
            blocks.append(Stripped("if (errors.Full()) return;"))
            blocks.append(enum_check_block)

    if len(blocks) == 0:
        blocks.append(Stripped(
            f'// There is no verification specified for {cls_name}.'))

    arg_name = csharp_naming.argument_name(cls.name)

    assert arg_name != 'path', "Unexpected reserved argument name"
    assert arg_name != 'errors', "Unexpected reserved argument name"

    writer = io.StringIO()
    writer.write(textwrap.dedent(f'''\
        /// <summary>
        /// Verify the given <paramref name={xml.sax.saxutils.quoteattr(arg_name)} /> and 
        /// append any errors to <paramref name="Errors" />.
        ///
        /// The <paramref name="path" /> localizes the <paramref name={xml.sax.saxutils.quoteattr(arg_name)} />.
        /// </summary>
        public static void Verify{cls_name} (
        {csharp_common.INDENT}{cls_name} {arg_name},
        {csharp_common.INDENT}string path,
        {csharp_common.INDENT}Errors errors)
        {{
        '''))

    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n\n')
        writer.write(textwrap.indent(block, csharp_common.INDENT))

    writer.write('\n}')

    return Stripped(writer.getvalue()), None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _generate_implementation(
        symbol_table: intermediate.SymbolTable,
        spec_impls: specific_implementations.SpecificImplementations
) -> Tuple[Optional[Stripped], Optional[List[Error]]]:
    """Generate a private static class, ``Implementation``, with verification logic."""
    errors = []  # type: List[Error]
    blocks = [
        _generate_enum_value_sets(symbol_table=symbol_table)
    ]  # type: List[Stripped]

    for symbol in symbol_table.symbols:
        if isinstance(symbol, (intermediate.Enumeration, intermediate.Interface)):
            continue

        if symbol.implementation_key is not None:
            verify_key = ImplementationKey(
                f'Verification/Implementation/verify_{symbol.name}')
            if verify_key not in spec_impls:
                errors.append(
                    Error(
                        symbol.parsed.node,
                        f"The implementation snippet is missing for "
                        f"the ``Verify`` method "
                        f"of the ``Verification.Implementation`` class: {verify_key}"))
                continue

            blocks.append(spec_impls[verify_key])
        else:
            implementation_verify, error = _generate_implementation_verify(cls=symbol)
            if error is not None:
                errors.append(error)
                continue

            if implementation_verify != '':
                blocks.append(implementation_verify)

    if len(errors) > 0:
        return None, errors

    writer = io.StringIO()
    writer.write(textwrap.dedent(f'''\
            /// <summary>
            /// Verify the instances of the model entities non-recursively.
            /// </summary>
            /// <remarks>
            /// The methods provided by this class are re-used in the verification
            /// visitors.
            /// </remarks>
            private static class Implementation
            {{
            '''))
    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n\n')

        writer.write(textwrap.indent(block, csharp_common.INDENT))

    writer.write('\n}  // private static class Implementation')

    return Stripped(writer.getvalue()), None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _generate_non_recursive_verifier(
        symbol_table: intermediate.SymbolTable
) -> Tuple[Optional[Stripped], Optional[List[Error]]]:
    """Generate the non-recursive verifier which visits the entities."""
    blocks = [
        Stripped("public readonly Errors Errors;"),
        Stripped(textwrap.dedent(f'''\
            /// <summary>
            /// Initialize the visitor with the given <paramref name="errors" />.
            ///
            /// The errors observed during the visitation will be appended to
            /// the <paramref name="errors" />.
            /// </summary>
            NonRecursiveVerifier(Errors errors)
            {{
            {csharp_common.INDENT}Errors = errors;
            }}''')),
        Stripped(textwrap.dedent(f'''\
            public void Visit(IEntity entity, string context)
            {{
            {csharp_common.INDENT}entity.Accept(this, context);
            }}'''))
    ]  # type: List[Stripped]

    for symbol in symbol_table.symbols:
        if not isinstance(symbol, intermediate.Class):
            continue

        arg_name = csharp_naming.argument_name(symbol.name)
        cls_name = csharp_naming.class_name(symbol.name)

        assert arg_name != 'context', "Unexpected reserved argument name"

        blocks.append(Stripped(textwrap.dedent(f'''\
            /// <summary>
            /// Verify <paramref name={xml.sax.saxutils.quoteattr(arg_name)} /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
            {csharp_common.INDENT}{cls_name} {arg_name},
            {csharp_common.INDENT}string context)
            {{
            {csharp_common.INDENT}Implementation.Verify{cls_name}(
            {csharp_common.INDENT2}{arg_name},
            {csharp_common.INDENT2}context,
            {csharp_common.INDENT2}Errors);
            }}''')))

    writer = io.StringIO()
    writer.write(textwrap.dedent(f'''\
        /// <summary>
        /// Verify the instances of the model entities non-recursively.
        /// </summary>
        public class NonRecursiveVerifier : 
        {csharp_common.INDENT}Visitation.IVisitorWithContext<string>
        {{
        '''))
    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n\n')

        writer.write(textwrap.indent(block, csharp_common.INDENT))

    writer.write('\n}  // public class NonRecursiveVerifier')

    return Stripped(writer.getvalue()), None


@require(lambda cls, prop: prop in cls.properties)
def _unroll_recursion_in_recursive_verify(
        cls: intermediate.Class,
        prop: intermediate.Property) -> Stripped:
    """Generate the code for unrolling the recursive visits  for the given property."""
    descendability = intermediate.map_descendability(prop.type_annotation)

    @require(lambda var_index: var_index >= 0)
    @require(lambda suffix: suffix in ("Item", "KeyValue"))
    def var_name(var_index: int, suffix: str) -> Identifier:
        """Generate the name of the loop variable."""
        if var_index == 0:
            if suffix == 'Item':
                return Identifier(f"an{suffix}")
            else:
                return Identifier(f"a{suffix}")

        elif var_index == 1:
            return Identifier(f"another{suffix}")
        else:
            return Identifier("yet" + "Yet" * (var_index - 1) + f"another{suffix}")

    def unroll(
            current_var_name: str,
            item_count: int,
            key_value_count: int,
            path: List[str],
            type_anno: intermediate.TypeAnnotation
    ) -> List[csharp_unrolling.Node]:
        """Generate the node corresponding to the ``type_anno`` and recurse."""
        if isinstance(type_anno, intermediate.BuiltinAtomicTypeAnnotation):
            return []

        elif isinstance(type_anno, intermediate.OurAtomicTypeAnnotation):
            if isinstance(type_anno.symbol, intermediate.Enumeration):
                return []

            joined_pth = '/'.join(path)
            return [csharp_unrolling.Node(
                text=textwrap.dedent(f'''\
                    if (Errors.Full()) return;
                    Visit(
                        {current_var_name},
                        ${csharp_common.string_literal(joined_pth)});'''),
                children=[])]

        elif isinstance(type_anno, (
                intermediate.ListTypeAnnotation, intermediate.SequenceTypeAnnotation,
                intermediate.SetTypeAnnotation)):

            if item_count > 15:
                index_var = f'i{item_count}'
            else:
                index_var = chr(ord('i') + item_count)

            children = unroll(
                current_var_name=f'{current_var_name}[{index_var}]',
                item_count=item_count + 1,
                key_value_count=key_value_count,
                path=path + [f'{{{index_var}}}'],
                type_anno=type_anno.items)

            if len(children) == 0:
                return []

            text = Stripped(
                f'for(var {index_var} = 0; '
                f'{index_var} < {current_var_name}.Count; '
                f'{index_var}++)')

            # Break into lines if too long.
            # This is just a heuristics — we do not consider the actual indention.
            if len(text) > 50:
                text = Stripped(textwrap.dedent(f'''\
                    for(
                    {csharp_common.INDENT}var {index_var} = 0;
                    {csharp_common.INDENT}{index_var} < {current_var_name}.Count;
                    {csharp_common.INDENT}{index_var}++)'''))

            return [csharp_unrolling.Node(text=text, children=children)]

        elif isinstance(type_anno, (
                intermediate.MappingTypeAnnotation,
                intermediate.MutableMappingTypeAnnotation
        )):
            key_value_var = var_name(key_value_count + 1, "KeyValue")

            children = unroll(
                current_var_name=f'{key_value_var}.Value',
                item_count=item_count,
                key_value_count=key_value_count + 1,
                path=path + [f'{{{key_value_var}.Key}}'],
                type_anno=type_anno.values)

            if len(children) > 0:
                return [csharp_unrolling.Node(
                    text=f'foreach (var {key_value_var} in {current_var_name})',
                    children=children)]
            else:
                return []

        elif isinstance(type_anno, intermediate.OptionalTypeAnnotation):
            children = unroll(
                current_var_name=current_var_name,
                item_count=item_count,
                key_value_count=key_value_count,
                path=path,
                type_anno=type_anno.value)
            if len(children) > 0:
                return [csharp_unrolling.Node(
                    text=f"if ({current_var_name} != null)", children=children)]
            else:
                return []
        else:
            assert_never(type_anno)

    arg_name = csharp_naming.argument_name(cls.name)
    prop_name = csharp_naming.property_name(prop.name)

    roots = unroll(
        current_var_name=f'{arg_name}.{prop_name}',
        item_count=0,
        key_value_count=0,
        path=['{context}', prop_name],
        type_anno=prop.type_annotation)

    if len(roots) == 0:
        return Stripped('')

    blocks = [csharp_unrolling.render(root) for root in roots]
    return Stripped('\n\n'.join(blocks))


# fmt: on
@require(
    lambda cls:
    cls.implementation_key is None,
    "Implementation-specific classes are handled elsewhere"
)
# fmt: off
def _generate_recursive_verifier_visit(
        cls: intermediate.Class
) -> Stripped:
    """Generate the ``Visit`` method of the ``RecursiveVerifier`` for the ``cls``."""
    arg_name = csharp_naming.argument_name(cls.name)
    cls_name = csharp_naming.class_name(cls.name)

    assert arg_name != 'context', "Unexpected reserved argument name"

    writer = io.StringIO()
    writer.write(textwrap.dedent(f'''\
        /// <summary>
        /// Verify recursively <paramref name={xml.sax.saxutils.quoteattr(arg_name)} /> and
        /// append any error to <see cref="Errors" /> 
        /// where <paramref name="context" /> is used to localize the error.
        /// </summary>
        public void Visit(
        {csharp_common.INDENT}{cls_name} {arg_name},
        {csharp_common.INDENT}string context)
        {{
        '''))

    blocks = [
        Stripped(textwrap.dedent(f'''\
        Implementation.Verify{cls_name}(
        {csharp_common.INDENT}{arg_name},
        {csharp_common.INDENT}context,
        {csharp_common.INDENT}Errors);'''))
    ]  # type: List[Stripped]

    # region Unroll

    recursion_ends_here = True
    for prop in cls.properties:
        unrolled_prop_verification = _unroll_recursion_in_recursive_verify(
            cls=cls,
            prop=prop)

        if unrolled_prop_verification != '':
            blocks.append(unrolled_prop_verification)
            recursion_ends_here = False

    if recursion_ends_here:
        blocks.append(Stripped("// The recursion ends here."))
    # endregion

    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n\n')

        writer.write(textwrap.indent(block, csharp_common.INDENT))

    writer.write('\n}')
    return Stripped(writer.getvalue())


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _generate_recursive_verifier(
        symbol_table: intermediate.SymbolTable,
        spec_impls: specific_implementations.SpecificImplementations
) -> Tuple[Optional[Stripped], Optional[List[Error]]]:
    """Generate the ``Verifier`` class which visits the entities and verifies them."""
    blocks = [
        Stripped("public readonly Errors Errors;"),
        Stripped(textwrap.dedent(f'''\
            /// <summary>
            /// Initialize the visitor with the given <paramref name="errors" />.
            ///
            /// The errors observed during the visitation will be appended to
            /// the <paramref name="errors" />.
            /// </summary>
            RecursiveVerifier(Errors errors)
            {{
            {csharp_common.INDENT}Errors = errors;
            }}''')),
        Stripped(textwrap.dedent(f'''\
            public void Visit(IEntity entity, string context)
            {{
            {csharp_common.INDENT}entity.Accept(this, context);
            }}'''))
    ]  # type: List[Stripped]

    errors = []  # type: List[Error]

    for symbol in symbol_table.symbols:
        if not isinstance(symbol, intermediate.Class):
            continue

        if symbol.implementation_key is not None:
            visit_key = ImplementationKey(
                f'Verification/RecursiveVerifier/visit_{symbol.name}')
            if visit_key not in spec_impls:
                errors.append(
                    Error(
                        symbol.parsed.node,
                        f"The implementation snippet is missing for "
                        f"the ``Visit`` method "
                        f"of the ``Verification.RecursiveVerifier`` class: "
                        f"{visit_key}"))
                continue

            blocks.append(spec_impls[visit_key])
        else:
            blocks.append(_generate_recursive_verifier_visit(cls=symbol))

    if len(errors) > 0:
        return None, errors

    writer = io.StringIO()
    writer.write(textwrap.dedent(f'''\
        /// <summary>
        /// Verify the instances of the model entities recursively.
        /// </summary>
        public class RecursiveVerifier : 
        {csharp_common.INDENT}Visitation.IVisitorWithContext<string>
        {{
        '''))
    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n\n')

        writer.write(textwrap.indent(block, csharp_common.INDENT))

    writer.write('\n}  // public class RecursiveVerifier')

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
        symbol_table: intermediate.SymbolTable,
        namespace: csharp_common.NamespaceIdentifier,
        spec_impls: specific_implementations.SpecificImplementations
) -> Tuple[Optional[str], Optional[List[Error]]]:
    """
    Generate the C# code of the structures based on the symbol table.

    The ``namespace`` defines the C# namespace.
    """
    blocks = [csharp_common.WARNING]  # type: List[Rstripped]

    using_directives = [
        "using ArgumentException = System.ArgumentException;\n"
        "using InvalidOperationException = System.InvalidOperationException;\n"
        "using NotImplementedException = System.NotImplementedException;\n"
        "using Regex = System.Text.RegularExpressions.Regex;\n"
        "using System.Collections.Generic;  // can't alias\n"
        "using System.Collections.ObjectModel;  // can't alias\n"
        "using System.Linq;  // can't alias"
    ]  # type: List[str]

    blocks.append(Stripped("\n".join(using_directives)))

    verification_blocks = [
        _generate_pattern_class(spec_impls=spec_impls),
        spec_impls[ImplementationKey('Verification/Error')],
        spec_impls[ImplementationKey('Verification/Errors')]
    ]  # type: List[Stripped]

    errors = []  # type: List[Error]

    implementation, implementation_errors = _generate_implementation(
        symbol_table=symbol_table, spec_impls=spec_impls)
    if implementation_errors:
        errors.extend(implementation_errors)
    else:
        verification_blocks.append(implementation)

    non_recursive, non_recursive_errors = _generate_non_recursive_verifier(
        symbol_table=symbol_table)

    if non_recursive_errors is not None:
        errors.extend(non_recursive_errors)
    else:
        verification_blocks.append(non_recursive)

    recursive, recursive_errors = _generate_recursive_verifier(
        symbol_table=symbol_table,
        spec_impls=spec_impls)

    if recursive_errors is not None:
        errors.extend(recursive_errors)
    else:
        verification_blocks.append(recursive)

    if len(errors) > 0:
        return None, errors

    verification_writer = io.StringIO()
    verification_writer.write(f"namespace {namespace}\n{{\n")
    verification_writer.write(
        f"{csharp_common.INDENT}public static class Verification\n"
        f"{csharp_common.INDENT}{{\n")

    for i, verification_block in enumerate(verification_blocks):
        if i > 0:
            verification_writer.write('\n\n')

        verification_writer.write(
            textwrap.indent(verification_block, 2 * csharp_common.INDENT))

    verification_writer.write(
        f"\n{csharp_common.INDENT}}}  // public static class Verification")
    verification_writer.write(f"\n}}  // namespace {namespace}")

    blocks.append(Stripped(verification_writer.getvalue()))

    blocks.append(csharp_common.WARNING)

    out = io.StringIO()
    for i, block in enumerate(blocks):
        if i > 0:
            out.write('\n\n')

        assert not block.startswith('\n')
        assert not block.endswith('\n')
        out.write(block)

    out.write('\n')

    return out.getvalue(), None

# endregion
