"""Generate Go code to handle asset administration shells based on the meta-model"""


from typing import TextIO
from aas_core_codegen import run, specific_implementations
from aas_core_codegen.golang import (
    structure as golang_structure,
    jsonization as golang_jsonization,
)


def execute(context: run.Context, stdout: TextIO, stderr: TextIO) -> int:

    package_name_key = specific_implementations.ImplementationKey("packagename.txt")
    package_name_text = context.spec_impls.get(package_name_key, None)

    if package_name_text is None:
        stderr.write(f"The packagename snippet is missing: {package_name_key}")
        return 1

    # -------
    # Structure
    # -------
    code, errors = golang_structure.generate(
        symbol_table=context.symbol_table,
        package_name=package_name_text,
        spec_impls=context.spec_impls,
    )

    if errors is not None:
        run.write_error_report(
            message=f"Failed to generate the structures in the Go code "
            f"based on {context.model_path}",
            errors=[context.lineno_columner(error) for error in errors],
            stderr=stderr,
        )
        return 1

    assert code is not None

    pth = context.output_dir / "types.go"
    pth.parent.mkdir(exist_ok=True)

    try:
        pth.write_text(code)
    except Exception as exception:
        run.write_error_report(
            message=f"Failed to write the structure Go code to ${pth}"
            f"based on {context.model_path}",
            errors=[str(exception)],
            stderr=stderr,
        )

    # -------
    # Jsonization
    # -------

    code, errors = golang_jsonization.generate(
        symbol_table=context.symbol_table,
        package_name=package_name_text,
        spec_impls=context.spec_impls,
    )

    if errors is not None:
        run.write_error_report(
            message=f"Failed to write the jsonization Go code"
            f"based on {context.model_path}",
            errors=[context.lineno_columner.error_message(error) for error in errors],
            stderr=stderr,
        )

    assert code is not None

    pth = context.output_dir / "json.go"

    pth.parent.mkdir(exist_ok=True)

    try:
        pth.write_text(code)

    except Exception as exception:
        run.write_error_report(
            message=f"Failed to write the jsonization Go code to {pth}",
            errors=[str(exception)],
            stderr=stderr,
        )
        return 1

    stdout.write(f"Code generated to: {context.output_dir}\n")
    return 0
