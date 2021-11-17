import ast
import io
import os
import pathlib
import textwrap
import unittest
from typing import Optional, Tuple

import asttokens
import docutils.nodes

import tests.common
from aas_core_csharp_codegen import parse
from aas_core_csharp_codegen.common import Error, LinenoColumner, Identifier


class Test_parsing_AST(unittest.TestCase):
    def test_valid_code(self) -> None:
        source = textwrap.dedent(
            """\
            class Something:
                pass
            """)

        atok, error = parse.source_to_atok(source=source)
        assert atok is not None
        assert error is None

    def test_invalid_code(self) -> None:
        source = textwrap.dedent(
            """\
            class Something: 12 this is wrong
            """)

        atok, error = parse.source_to_atok(source=source)
        assert error is not None
        assert isinstance(error, SyntaxError)
        self.assertEqual(1, error.lineno)


class Test_checking_imports(unittest.TestCase):
    def test_import_reported(self) -> None:
        source = textwrap.dedent(
            """\
            import typing
            """)

        atok, error = parse.source_to_atok(source=source)
        assert atok is not None

        errors = parse.check_expected_imports(atok=atok)
        self.assertListEqual(
            [
                'At line 1 and column 1: '
                'Unexpected ``import ...``. '
                'Only ``from ... import...`` statements are expected.'
            ], errors)

    def test_from_import_as_reported(self) -> None:
        source = textwrap.dedent(
            """\
            from typing import List as Lst
            """)

        atok, error = parse.source_to_atok(source=source)
        assert atok is not None

        errors = parse.check_expected_imports(atok=atok)
        self.assertListEqual(
            [
                'At line 1 and column 1: Unexpected ``from ... import ... as ...``. '
                'Only ``from ... import...`` statements are expected.'
            ], errors)

    def test_unexpected_name_from_module(self) -> None:
        source = textwrap.dedent(
            """\
            from enum import List
            """)

        atok, error = parse.source_to_atok(source=source)
        assert atok is not None
        assert error is None

        errors = parse.check_expected_imports(atok=atok)
        self.assertListEqual(
            [
                "At line 1 and column 1: "
                "Expected to import 'List' from the module typing, "
                "but it is imported from enum."
            ], errors)

    def test_unexpected_import_from_a_module(self) -> None:
        source = textwrap.dedent(
            """\
            from something import Else
            """)

        atok, error = parse.source_to_atok(source=source)
        assert atok is not None
        assert error is None

        errors = parse.check_expected_imports(atok=atok)
        self.assertListEqual(
            [
                "At line 1 and column 1: Unexpected import of a name 'Else'."
            ], errors)


class Test_parsing_docstring(unittest.TestCase):
    @staticmethod
    def parse_and_extract_docstring(source: str) -> docutils.nodes.document:
        """
        Parse the ``source`` and extract a description.

        The description is expected to belong to a single class, ``Some_class``.
        """
        symbol_table, error = tests.common.parse_source(source)
        assert error is None, f'{error}'

        symbol = symbol_table.must_find_class(Identifier('Some_class'))
        return symbol.description.document

    def test_empty(self) -> None:
        source = textwrap.dedent('''\
            class Some_class:
                """"""
            ''')

        document = Test_parsing_docstring.parse_and_extract_docstring(source=source)

        self.assertEqual(0, len(document.children))

    def test_simple_single_line(self) -> None:
        source = textwrap.dedent('''\
            class Some_class:
                """This is some documentation."""
            ''')

        document = Test_parsing_docstring.parse_and_extract_docstring(source=source)

        self.assertEqual(1, len(document.children))
        self.assertIsInstance(document.children[0], docutils.nodes.paragraph)

    def test_that_multi_line_docstring_is_not_parsed_as_a_block_quote(self) -> None:
        source = textwrap.dedent('''\
            class Some_class:
                """
                This is some documentation.

                Another paragraph.
                """
            ''')

        document = Test_parsing_docstring.parse_and_extract_docstring(source=source)
        self.assertEqual(2, len(document.children))
        self.assertIsInstance(document.children[0], docutils.nodes.paragraph)
        self.assertIsInstance(document.children[1], docutils.nodes.paragraph)



class Test_against_recorded(unittest.TestCase):
    # Set this variable to True if you want to re-record the test data,
    # without any checks
    RERECORD = False

    def test_cases(self) -> None:
        this_dir = pathlib.Path(os.path.realpath(__file__)).parent
        test_cases_dir = this_dir.parent / "test_data/test_parse"

        assert test_cases_dir.exists(), f"{test_cases_dir=}"
        assert test_cases_dir.is_dir(), f"{test_cases_dir=}"

        for source_pth in test_cases_dir.glob("**/source.py"):
            case_dir = source_pth.parent

            expected_symbol_table_pth = case_dir / "expected_symbol_table.txt"
            expected_error_pth = case_dir / "expected_error.txt"

            source = source_pth.read_text()
            symbol_table, error = tests.common.parse_source(source)

            symbol_table_str = (
                "" if symbol_table is None
                else parse.dump(symbol_table)
            )

            error_str = (
                "" if error is None
                else tests.common.most_underlying_message(error)
            )

            if Test_against_recorded.RERECORD:
                expected_symbol_table_pth.write_text(symbol_table_str)
                expected_error_pth.write_text(error_str)
            else:
                expected_symbol_table_str = expected_symbol_table_pth.read_text()
                self.assertEqual(
                    expected_symbol_table_str, symbol_table_str,
                    f"{case_dir=}, {error=}")

                expected_error_str = expected_error_pth.read_text()
                self.assertEqual(expected_error_str, error_str, f"{case_dir=}")


class Test_unexpected_class_definitions(unittest.TestCase):
    @staticmethod
    def error_from_source(source: str) -> Optional[Error]:
        """Encapsulate the observation of the error when parsing a class."""
        atok, parse_exception = parse.source_to_atok(source=source)
        assert parse_exception is None, f'{parse_exception=}'
        assert atok is not None

        symbol_table, error = parse.atok_to_symbol_table(atok=atok)
        return error


class Test_parse_type_annotation(unittest.TestCase):
    @staticmethod
    def parse_type_annotation_from_ann_assign(
            source: str
    ) -> Tuple[ast.AST, asttokens.ASTTokens]:
        """Encapsulate the parsing of the type annotation of a variable."""
        atok = asttokens.ASTTokens(source, parse=True)

        module = atok.tree
        assert isinstance(module, ast.Module)
        assert len(module.body) == 1, f'{module.body=}'

        ann_assign = module.body[0]
        assert isinstance(ann_assign, ast.AnnAssign), f'{ann_assign=}'

        assert ann_assign.annotation is not None

        return ann_assign.annotation, atok

    def test_atomic(self) -> None:
        anno, atok = Test_parse_type_annotation.parse_type_annotation_from_ann_assign(
            "x: int")

        type_annotation, error = parse._translate._type_annotation(node=anno, atok=atok)
        assert error is None, f"{error=}"

        self.assertEqual("int", str(type_annotation))

    def test_subscripted(self) -> None:
        anno, atok = Test_parse_type_annotation.parse_type_annotation_from_ann_assign(
            "x: Mapping[str, Optional[int]]")

        type_annotation, error = parse._translate._type_annotation(node=anno, atok=atok)
        assert error is None, f"{error=}"

        self.assertEqual("Mapping[str, Optional[int]]", str(type_annotation))

    def test_nested(self) -> None:
        anno, atok = Test_parse_type_annotation.parse_type_annotation_from_ann_assign(
            "x: Optional[List[Reference]]")

        type_annotation, error = parse._translate._type_annotation(node=anno, atok=atok)
        assert error is None, f"{error=}"

        self.assertEqual("Optional[List[Reference]]", str(type_annotation))


class Test_parse_type_annotation_fail(unittest.TestCase):
    def test_ellipsis(self) -> None:
        anno, atok = Test_parse_type_annotation.parse_type_annotation_from_ann_assign(
            "x: Mapping[str, ...]")

        type_annotation, error = parse._translate._type_annotation(node=anno, atok=atok)
        assert error is not None

        self.assertEqual(
            "Expected a string literal if the type annotation is given as a constant, "
            "but got: Ellipsis (as <class 'ellipsis'>)",
            error.message)

    def test_non_name_type_identifier(self) -> None:
        anno, atok = Test_parse_type_annotation.parse_type_annotation_from_ann_assign(
            "x: (int if True else str)")

        type_annotation, error = parse._translate._type_annotation(node=anno, atok=atok)
        assert error is not None

        self.assertEqual(
            "Expected either atomic type annotation (as name or string literal) "
            "or a subscripted one (as a subscript), "
            "but got: int if True else str (as <class '_ast.IfExp'>)",
            error.message)

    def test_unexpected_slice_in_index(self) -> None:
        anno, atok = Test_parse_type_annotation.parse_type_annotation_from_ann_assign(
            "x: Optional[str:int]")

        type_annotation, error = parse._translate._type_annotation(node=anno, atok=atok)
        assert error is not None

        self.assertEqual(
            "Expected an index to define a subscripted type annotation, "
            "but got: str:int",
            error.message)

    def test_unexpected_expression_in_index(self) -> None:
        anno, atok = Test_parse_type_annotation.parse_type_annotation_from_ann_assign(
            "x: Optional[str if True else int]")

        type_annotation, error = parse._translate._type_annotation(node=anno, atok=atok)
        assert error is not None

        self.assertEqual(
            "Expected a tuple, a name, a subscript or a string literal "
            "for a subscripted type annotation, but got: str if True else int",
            error.message)


class Test_against_real_meta_models(unittest.TestCase):
    def test_smoke_on_files(self) -> None:
        for meta_model_pth in tests.common.list_valid_meta_models_from_test_data():
            source = meta_model_pth.read_text()

            atok, parse_exception = parse.source_to_atok(source=source)
            assert parse_exception is None, f"{meta_model_pth=}, {parse_exception=}"
            assert atok is not None

            import_errors = parse.check_expected_imports(atok=atok)
            assert not import_errors, f"{meta_model_pth=}, {import_errors=}"

            symbol_table, parse_error = parse.atok_to_symbol_table(atok=atok)
            if parse_error is not None:
                writer = io.StringIO()
                writer.write(
                    f"Failed to construct the symbol table "
                    f"from the file: {meta_model_pth}\n")

                lineno_columner = LinenoColumner(atok=atok)
                writer.write(f"{lineno_columner.error_message(parse_error)}\n")

                raise AssertionError(writer.getvalue())

            assert symbol_table is not None


if __name__ == "__main__":
    unittest.main()
