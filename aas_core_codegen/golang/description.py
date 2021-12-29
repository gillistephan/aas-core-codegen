"""Gender descriptions to Go code"""
from icontract import ensure
from typing import Tuple, Optional, List
import docutils.nodes
import docutils.utils
import xml.sax.saxutils

from aas_core_codegen.common import Stripped, Error
from aas_core_codegen import intermediate
from aas_core_codegen.intermediate import (
    rendering as intermediate_rendering,
    doc as intermediate_doc,
)

# Godocs are straight forward, they don't have any language constructs or
# machine readable syntax. They are just "comments".
class _ElementRenderer(intermediate_rendering.DocutilsElementTransformer[str]):
    def transform_text(
        self, element: docutils.nodes.Text
    ) -> Tuple[Optional[str], Optional[str]]:
        return xml.sax.saxutils.escape(element.astext()), None

    def transform_symbol_reference_in_doc(
        self, element: intermediate_doc.SymbolReference
    ) -> Tuple[Optional[str], Optional[str]]:
        return f"//TODO: transform_symbol_reference_in_doc NOT_IMPLEMENTED", None

    def transform_attribute_reference_in_doc(
        self, element: intermediate_doc.AttributeReference
    ) -> Tuple[Optional[str], Optional[str]]:
        return f"//TODO: transform_attribute_reference_in_doc NOT_IMPLEMENTED", None

    def transform_argument_reference_in_doc(
        self, element: intermediate_doc.ArgumentReference
    ) -> Tuple[Optional[str], Optional[str]]:
        return f"//TODO: transform_argument_reference_in_doc NOT_IMPLEMENTED", None

    def transform_literal(
        self, element: docutils.nodes.literal
    ) -> Tuple[Optional[str], Optional[str]]:
        return f"//TODO: transform_literal NOT_IMPLEMENTED", None

    @ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
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

    @ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
    def transform_emphasis(
        self, element: docutils.nodes.emphasis
    ) -> Tuple[Optional[str], Optional[str]]:
        return f"//TODO: transform_emphasis NOT_IMPLEMENTED", None

    @ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
    def transform_list_item(
        self, element: docutils.nodes.list_item
    ) -> Tuple[Optional[str], Optional[str]]:
        return f"//TODO: transform_list_item NOT_IMPLEMENTED", None

    @ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
    def transform_bullet_list(
        self, element: docutils.nodes.bullet_list
    ) -> Tuple[Optional[str], Optional[str]]:
        return f"//TODO: transform_bullet_list NOT_IMPLEMENTED", None

    @ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
    def transform_note(
        self, element: docutils.nodes.note
    ) -> Tuple[Optional[str], Optional[str]]:
        return f"//TODO: transform_note NOT_IMPLEMENTED", None

    @ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
    def transform_reference(
        self, element: docutils.nodes.reference
    ) -> Tuple[Optional[str], Optional[str]]:
        return f"//TODO: transform_reference NOT_IMPLEMENTED", None

    @ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
    def transform_document(
        self, element: docutils.nodes.document
    ) -> Tuple[Optional[str], Optional[str]]:

        summary = None  # type: Optional[docutils.nodes.paragraph]
        remarks = []  # type: List[docutils.nodes.Element]
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
                (
                    docutils.nodes.paragraph,
                    docutils.nodes.bullet_list,
                    docutils.nodes.note,
                ),
            ):
                remarks.append(child)
            else:
                tail = remainder[i:]
                break

        blocks = []  # type: List[Stripped]

        renderer = _ElementRenderer()

        if summary:
            summary_text, error = renderer.transform(element=summary)
            if error:
                return None, error

            assert summary_text is not None
            blocks.append(f"{summary_text}\n")

        # fmt: off
        text = '\n'.join(
            f'// {line}'
            for line in '\n'.join(blocks).splitlines()
        )
        # fmt: on
        return text, None


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def generate_comment(
    description: intermediate.Description,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """Generate a documentation comment based on the doc string."""

    if len(description.document.children) == 0:
        return Stripped(""), None

    renderer = _ElementRenderer()
    text, error = renderer.transform(description.document)
    if error:
        return None, Error(description.node, error)

    assert text is not None
    return Stripped(text), None
