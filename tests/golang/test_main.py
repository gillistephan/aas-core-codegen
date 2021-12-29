import contextlib
import io
import os
import pathlib
import unittest
import subprocess


import aas_core_codegen.main


class Test_for_debugging(unittest.TestCase):
    def test_cases(self) -> None:
        repo_dir = pathlib.Path(os.path.realpath(__file__)).parent.parent.parent
        parent_case_dir = repo_dir / "test_data" / "test_golang" / "test_main"

        assert parent_case_dir.exists() and parent_case_dir.is_dir(), parent_case_dir

        for case_dir in parent_case_dir.iterdir():
            assert case_dir.is_dir(), case_dir

            model_pth = case_dir / "input/meta_model.py"
            assert model_pth.exists() and model_pth.is_file(), model_pth

            snippets_dir = case_dir / "input/snippets"
            assert snippets_dir.exists() and snippets_dir.is_dir(), snippets_dir

            expected_output_dir = case_dir / "expected_output"

            with contextlib.ExitStack() as exit_stack:

                output_dir = expected_output_dir

                params = aas_core_codegen.main.Parameters(
                    model_path=model_pth,
                    target=aas_core_codegen.main.Target.GOLANG,
                    snippets_dir=snippets_dir,
                    output_dir=pathlib.Path(output_dir),
                )

                stdout = io.StringIO()
                stderr = io.StringIO()

                return_code = aas_core_codegen.main.execute(
                    params=params, stdout=stdout, stderr=stderr
                )

                if stderr.getvalue() != "":
                    return AssertionError(
                        f"Expected no stderr on valid models, but got: \n"
                        f"{stderr.getvalue()}"
                    )

                self.assertEqual(
                    0, return_code, "Expected 0 return code on valid models"
                )

                subprocess.call(
                    f"cd {output_dir} && gofmt -w types.go json.go",
                    shell=True,
                )


if __name__ == "__main__":
    unittest.main()
