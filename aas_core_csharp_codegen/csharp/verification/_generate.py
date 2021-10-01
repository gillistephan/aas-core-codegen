"""Generate the invariant verifiers from the intermediate representation."""
import textwrap
from typing import Tuple, Optional, List

from icontract import require, ensure

from aas_core_csharp_codegen import intermediate
import aas_core_csharp_codegen.csharp.common as csharp_common
import aas_core_csharp_codegen.csharp.naming as csharp_naming

from aas_core_csharp_codegen.common import Error, Stripped, Rstripped
from aas_core_csharp_codegen.csharp import specific_implementations

# region Verify
from aas_core_csharp_codegen.specific_implementations import ImplementationKey


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

# fmt: off
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
@ensure(
    lambda result:
    not (result[0] is not None) or result[0].endswith('\n'),
    "Trailing newline mandatory for valid end-of-files"
)
# fmt: on
def generate(
        intermediate_symbol_table: intermediate.SymbolTable,
        namespace: csharp_common.NamespaceIdentifier,
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
        "using Regex = System.Text.RegularExpressions.Regex;"
        "using System.Collections.Generic;  // can't alias"
    ]  # type: List[str]

    if len(using_directives) > 0:
        blocks.append(Stripped("\n".join(using_directives)))

    blocks.append(Stripped(f"namespace {namespace}.Verification\n{{"))

    errors = []  # type: List[Error]

    for intermediate_symbol in intermediate_symbol_table.symbols:
        code = None  # type: Optional[Stripped]
        error = None  # type: Optional[Error]

        if (
                isinstance(intermediate_symbol, intermediate.Class)
                and intermediate_symbol.implementation_key is not None
        ):
            code = spec_impls[intermediate_symbol.implementation_key]
        else:
            if isinstance(intermediate_symbol, intermediate.Enumeration):
                # TODO: test
                code, error = _generate_enum(symbol=intermediate_symbol)
            elif isinstance(intermediate_symbol, intermediate.Interface):
                # TODO: test
                code, error = _generate_interface(
                    symbol=intermediate_symbol)

            elif isinstance(intermediate_symbol, intermediate.Class):
                code, error = _generate_class(
                    symbol=intermediate_symbol,
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

    out = io.StringIO()
    for i, block in enumerate(blocks):
        if i > 0:
            out.write('\n\n')

        out.write(block)

    out.write('\n')

    return out.getvalue(), None

# endregion
