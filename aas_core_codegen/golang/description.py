"""Gender descriptions to Go code"""
from icontract import ensure
from typing import Tuple, Optional
import docutils.nodes
import docutils.utils
import xml.sax.saxutils

from aas_core_codegen.common import Stripped, Error
from aas_core_codegen import intermediate
from aas_core_codegen.intermediate import (
    rendering as intermediate_rendering,
    doc as intermediate_doc,
)


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
        return f"//TODO: transform_paragraph NOT_IMPLEMENTED", None

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
        return f"//TODO: transform_document NOT_IMPLEMENTED", None


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
