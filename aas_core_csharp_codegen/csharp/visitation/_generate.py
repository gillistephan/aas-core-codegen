"""Generate the visitor classes based on the intermediate representation."""

"""Generate the invariant verifiers from the intermediate representation."""
import io
import textwrap
import xml.sax.saxutils
from typing import Tuple, Optional, List, Union

from icontract import ensure, require

import aas_core_csharp_codegen.csharp.common as csharp_common
import aas_core_csharp_codegen.csharp.naming as csharp_naming
from aas_core_csharp_codegen import intermediate
from aas_core_csharp_codegen.common import Error, Stripped, Rstripped, Identifier, \
    assert_never
from aas_core_csharp_codegen.csharp import specific_implementations
from aas_core_csharp_codegen.specific_implementations import ImplementationKey


# region Generate

def _generate_ivisitor(
        symbol_table: intermediate.SymbolTable
) -> Stripped:
    """Generate the visitor interface."""
    blocks = []  # type: List[Stripped]

    for symbol in symbol_table.symbols:
        if isinstance(symbol, intermediate.Enumeration):
            continue

        elif isinstance(symbol, intermediate.Interface):
            continue

        elif isinstance(symbol, intermediate.Class):
            cls_name = csharp_naming.class_name(symbol.name)
            var_name = csharp_naming.argument_name(symbol.name)
            blocks.append(Stripped(f'public void Visit({cls_name} {var_name});'))

        else:
            assert_never(symbol)

    writer = io.StringIO()
    writer.write(
        textwrap.dedent('''\
            /// <summary>
            /// Define the interface for a visitor which visits the instances of the model.
            /// </summary>
            public interface IVisitor
            {
                public void Visit(IEntity entity);
            '''))

    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n')
        writer.write(textwrap.indent(block, csharp_common.INDENT))

    writer.write(f'\n}}  // public interface IVisitor')

    return Stripped(writer.getvalue())


def _generate_visitor_through(
        symbol_table: intermediate.SymbolTable
) -> Stripped:
    """Generate the visitor that simply iterates over the instances."""
    blocks = []  # type: List[Stripped]

    for symbol in symbol_table.symbols:
        if isinstance(symbol, intermediate.Enumeration):
            continue

        elif isinstance(symbol, intermediate.Interface):
            continue

        elif isinstance(symbol, intermediate.Class):
            cls_name = csharp_naming.class_name(symbol.name)
            var_name = csharp_naming.argument_name(symbol.name)
            blocks.append(Stripped(textwrap.dedent(f'''\
                public void Visit({cls_name} {var_name})
                {{
                    // Just descend through, do nothing with the {var_name}
                    foreach (var something in {var_name}.DescendOnce())
                    {{
                        Visit(something);
                    }}
                }}
                ''')))

        else:
            assert_never(symbol)

    writer = io.StringIO()
    writer.write(
        textwrap.dedent('''\
            /// <summary>
            /// Just descend through the instances without any action.
            /// </summary>
            /// <remarks>
            /// This class is meaningless for itself. However, it is a good base if you
            /// want to descend through instances and apply actions only on a subset of
            /// entities.
            /// </remarks> 
            public class VisitorThrough
            {
                public void Visit(IEntity entity)
                {{
                    entity.Accept(this);
                }}
            '''))

    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n')
        writer.write(textwrap.indent(block, csharp_common.INDENT))

    writer.write(f'\n}}  // public class VisitorThrough')

    return Stripped(writer.getvalue())


def _generate_ivisitor_with_context(
        symbol_table: intermediate.SymbolTable
) -> Stripped:
    """Generate the interface for the visitor with context."""
    blocks = []  # type: List[Stripped]

    for symbol in symbol_table.symbols:
        if isinstance(symbol, intermediate.Enumeration):
            continue

        elif isinstance(symbol, intermediate.Interface):
            continue

        elif isinstance(symbol, intermediate.Class):
            cls_name = csharp_naming.class_name(symbol.name)
            var_name = csharp_naming.argument_name(symbol.name)
            blocks.append(Stripped(
                f'public void Visit({cls_name} {var_name}, C context);'))

        else:
            assert_never(symbol)

    writer = io.StringIO()
    writer.write(
        textwrap.dedent('''\
            /// <summary>
            /// Define the interface for a visitor which visits the instances of the model.
            /// </summary>
            /// <typeparam name="C">Context type</typeparam>
            public interface IVisitorWithContext<C>
            {
                public void Visit(IEntity entity, C context);
            '''))

    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n')
        writer.write(textwrap.indent(block, csharp_common.INDENT))

    writer.write(f'\n}}  // public interface IVisitorWithContext')

    return Stripped(writer.getvalue())


def _generate_itransformer(
        symbol_table: intermediate.SymbolTable
) -> Stripped:
    """Generate the transformer interface."""
    blocks = []  # type: List[Stripped]

    for symbol in symbol_table.symbols:
        if isinstance(symbol, intermediate.Enumeration):
            continue

        elif isinstance(symbol, intermediate.Interface):
            continue

        elif isinstance(symbol, intermediate.Class):
            cls_name = csharp_naming.class_name(symbol.name)
            var_name = csharp_naming.argument_name(symbol.name)
            blocks.append(Stripped(f'public T Transform({cls_name} {var_name});'))

        else:
            assert_never(symbol)

    writer = io.StringIO()
    writer.write(
        textwrap.dedent('''\
            /// <summary>
            /// Define the interface for a transformer which transforms recursively 
            /// the instances into something else.
            /// </summary>
            /// <typeparam name="T">The type of the transformation result</typeparam>
            public interface ITransformer<T>
            {
                public T Transform(IEntity entity);
            '''))

    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n')
        writer.write(textwrap.indent(block, csharp_common.INDENT))

    writer.write(f'\n}}  // public interface ITransformer')

    return Stripped(writer.getvalue())


def _generate_itransformer_with_context(
        symbol_table: intermediate.SymbolTable
) -> Stripped:
    """Generate the interface for the transformer with context."""
    blocks = []  # type: List[Stripped]

    for symbol in symbol_table.symbols:
        if isinstance(symbol, intermediate.Enumeration):
            continue

        elif isinstance(symbol, intermediate.Interface):
            continue

        elif isinstance(symbol, intermediate.Class):
            cls_name = csharp_naming.class_name(symbol.name)
            var_name = csharp_naming.argument_name(symbol.name)
            blocks.append(Stripped(
                f'public T Transform({cls_name} {var_name}, C context);'))

        else:
            assert_never(symbol)

    writer = io.StringIO()
    writer.write(
        textwrap.dedent('''\
            /// <summary>
            /// Define the interface for a transformer which recursively transforms
            /// the instances into something else while the context is passed along.
            /// </summary>
            /// <typeparam name="T">The type of the transformation result</typeparam>
            /// <typeparam name="C">Context type</typeparam>
            public interface ITransformerWithContext<C, T>
            {
                public T Transform(IEntity entity, C context);
            '''))

    for i, block in enumerate(blocks):
        if i > 0:
            writer.write('\n')
        writer.write(textwrap.indent(block, csharp_common.INDENT))

    writer.write(f'\n}}  // public interface ITransformerWithContext')

    return Stripped(writer.getvalue())


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
        namespace: csharp_common.NamespaceIdentifier
) -> Tuple[Optional[str], Optional[List[Error]]]:
    """
    Generate the C# code of the visitors based on the intermediate representation

    The ``namespace`` defines the C# namespace.
    """
    blocks = [csharp_common.WARNING]  # type: List[Rstripped]

    writer = io.StringIO()
    writer.write(f"namespace {namespace}\n{{\n")
    writer.write(
        f"{csharp_common.INDENT}public static class Visitation\n"
        f"{csharp_common.INDENT}{{\n")

    visitation_blocks = [
        _generate_ivisitor(symbol_table=symbol_table),
        _generate_ivisitor_with_context(symbol_table=symbol_table),
        _generate_itransformer(symbol_table=symbol_table),
        _generate_itransformer_with_context(symbol_table=symbol_table)
    ]

    for i, visitation_block in enumerate(visitation_blocks):
        if i > 0:
            writer.write('\n\n')

        writer.write(
            textwrap.indent(visitation_block, csharp_common.INDENT2))

    writer.write(
        f"\n{csharp_common.INDENT}}}  // public static class Visitation")
    writer.write(f"\n}}  // namespace {namespace}")

    blocks.append(Stripped(writer.getvalue()))

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
