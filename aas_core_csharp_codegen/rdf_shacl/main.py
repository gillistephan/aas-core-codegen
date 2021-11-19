"""Generate the RDF ontology and the SHACL schema corresponding to the meta-model."""

import argparse
import pathlib
import sys
from typing import TextIO

import aas_core_csharp_codegen
import aas_core_csharp_codegen.rdf_shacl.rdf
import aas_core_csharp_codegen.rdf_shacl.shacl
from aas_core_csharp_codegen.rdf_shacl import (
    common as rdf_shacl_common
)
from aas_core_csharp_codegen import cli, parse, specific_implementations, \
    intermediate
from aas_core_csharp_codegen.common import LinenoColumner

# TODO: this needs to be moved to a separate package once we are done with
#  the development.

assert aas_core_csharp_codegen.rdf_shacl.__doc__ == __doc__


class Parameters:
    """Represent the program parameters."""

    def __init__(
            self,
            model_path: pathlib.Path,
            snippets_dir: pathlib.Path,
            output_dir: pathlib.Path
    ) -> None:
        """Initialize with the given values."""
        self.model_path = model_path
        self.snippets_dir = snippets_dir
        self.output_dir = output_dir


def run(params: Parameters, stdout: TextIO, stderr: TextIO) -> int:
    """Run the program."""
    # region Basic checks
    # TODO: test this failure case
    if not params.model_path.exists():
        stderr.write(f"The --model_path does not exist: {params.model_path}\n")
        return 1

    # TODO: test this failure case
    if not params.model_path.is_file():
        stderr.write(
            f"The --model_path does not point to a file: {params.model_path}\n")
        return 1

    # TODO: test this failure case
    if not params.snippets_dir.exists():
        stderr.write(f"The --snippets_dir does not exist: {params.snippets_dir}\n")
        return 1

    # TODO: test this failure case
    if not params.snippets_dir.is_dir():
        stderr.write(
            f"The --snippets_dir does not point to a directory: "
            f"{params.snippets_dir}\n")
        return 1

    # TODO: test the happy path
    if not params.output_dir.exists():
        params.output_dir.mkdir(parents=True, exist_ok=True)
    else:
        # TODO: test this failure case
        if not params.snippets_dir.is_dir():
            stderr.write(
                f"The --output_dir does not point to a directory: "
                f"{params.output_dir}\n")
            return 1

    # endregion

    # region Parse

    spec_impls, spec_impls_errors = (
        specific_implementations.read_from_directory(
            snippets_dir=params.snippets_dir))

    if spec_impls_errors:
        cli.write_error_report(
            message="Failed to resolve the implementation-specific "
                    "RDF and SHACL snippets",
            errors=spec_impls_errors,
            stderr=stderr)
        return 1

    text = params.model_path.read_text(encoding='utf-8')

    # TODO: test all the following individual failure cases
    atok, parse_exception = parse.source_to_atok(source=text)
    if parse_exception:
        if isinstance(parse_exception, SyntaxError):
            stderr.write(
                f"Failed to parse the meta-model {params.model_path}: "
                f"invalid syntax at line {parse_exception.lineno}\n"
            )
        else:
            stderr.write(
                f"Failed to parse the meta-model {params.model_path}: "
                f"{parse_exception}\n"
            )

        return 1

    import_errors = parse.check_expected_imports(atok=atok)
    if import_errors:
        cli.write_error_report(
            message="One or more unexpected imports in the meta-model",
            errors=import_errors,
            stderr=stderr,
        )

        return 1

    lineno_columner = LinenoColumner(atok=atok)

    parsed_symbol_table, error = parse.atok_to_symbol_table(atok=atok)
    if error is not None:
        cli.write_error_report(
            message=f"Failed to construct the symbol table from {params.model_path}",
            errors=[lineno_columner.error_message(error)],
            stderr=stderr,
        )

        return 1

    assert parsed_symbol_table is not None

    ir_symbol_table, error = intermediate.translate(
        parsed_symbol_table=parsed_symbol_table,
        atok=atok,
    )
    if error is not None:
        cli.write_error_report(
            message=f"Failed to translate the parsed symbol table "
                    f"to intermediate symbol table "
                    f"based on {params.model_path}",
            errors=[lineno_columner.error_message(error)],
            stderr=stderr,
        )

        return 1

    # endregion

    # region Dependencies

    symbol_to_rdfs_range, error = rdf_shacl_common.determine_symbol_to_rdfs_range(
        symbol_table=ir_symbol_table, spec_impls=spec_impls)
    if error:
        cli.write_error_report(
            message=f"Failed to determine the mapping symbol 🠒 ``rdfs:range`` "
                    f"based on {params.model_path}",
            errors=[lineno_columner.error_message(error)],
            stderr=stderr,
        )

        return 1

    url_prefix_key = specific_implementations.ImplementationKey(
        "url_prefix.txt"
    )
    url_prefix = spec_impls.get(url_prefix_key, None)
    if url_prefix is None:
        stderr.write(
            f"The implementation snippet for the URL prefix of the ontology "
            f"is missing: {url_prefix_key}\n")
        return 1

    # endregion

    # region RDF ontology

    rdf_code, errors = aas_core_csharp_codegen.rdf_shacl.rdf.generate(
        symbol_table=ir_symbol_table,
        symbol_to_rdfs_range=symbol_to_rdfs_range,
        spec_impls=spec_impls,
        url_prefix=url_prefix)

    if errors is not None:
        cli.write_error_report(
            message=f"Failed to generate the RDF ontology "
                    f"based on {params.model_path}",
            errors=[lineno_columner.error_message(error) for error in errors],
            stderr=stderr)
        return 1

    assert rdf_code is not None

    pth = params.output_dir / "rdf-ontology.ttl"
    try:
        pth.write_text(rdf_code)
    except Exception as exception:
        cli.write_error_report(
            message=f"Failed to write the RDF ontology to {pth}",
            errors=[str(exception)],
            stderr=stderr)
        return 1

    # endregion

    # region SHACL schema

    shacl_code, errors = aas_core_csharp_codegen.rdf_shacl.shacl.generate(
        symbol_table=ir_symbol_table,
        symbol_to_rdfs_range=symbol_to_rdfs_range,
        spec_impls=spec_impls,
        url_prefix=url_prefix)

    if errors is not None:
        cli.write_error_report(
            message=f"Failed to generate the SHACL schema "
                    f"based on {params.model_path}",
            errors=[lineno_columner.error_message(error) for error in errors],
            stderr=stderr)
        return 1

    assert shacl_code is not None

    pth = params.output_dir / "shacl-schema.ttl"
    try:
        pth.write_text(shacl_code)
    except Exception as exception:
        cli.write_error_report(
            message=f"Failed to write the SHACL schema to {pth}",
            errors=[str(exception)],
            stderr=stderr)
        return 1

    # endregion

    stdout.write(f"Code generated to: {params.output_dir}\n")
    return 0


def main(prog: str) -> int:
    """
    Execute the main routine.

    :param prog: name of the program to be displayed in the help
    :return: exit code
    """
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    parser.add_argument("--model_path", help="path to the meta-model", required=True)
    parser.add_argument(
        "--snippets_dir",
        help="path to the directory containing implementation-specific code snippets",
        required=True)
    parser.add_argument(
        "--output_dir", help="path to the generated code", required=True
    )
    args = parser.parse_args()

    params = Parameters(
        model_path=pathlib.Path(args.model_path),
        snippets_dir=pathlib.Path(args.snippets_dir),
        output_dir=pathlib.Path(args.output_dir),
    )

    run(params=params, stdout=sys.stdout, stderr=sys.stderr)

    return 0


def entry_point() -> int:
    """Provide an entry point for a console script."""
    return main(prog="aas-core-csharp-codegen")


if __name__ == "__main__":
    sys.exit(main("aas-core-csharp-codegen"))
