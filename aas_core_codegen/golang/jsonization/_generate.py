import io
from re import T
import textwrap
from icontract import ensure
from typing import Tuple, Optional, List

from aas_core_codegen import intermediate, naming, specific_implementations
from aas_core_codegen.golang import common as golang_common, naming as golang_naming
from aas_core_codegen.common import Error, Identifier, Stripped, assert_never


UNMARSHAL_JSON_FUNC_SIG = "unmarshalJSON(iter *json.Iterator) {"
MARSHAL_JSON_FUNC_SIG = "marshalJSON(stream *json.Stream) {"
READ_OBJECT_LOOP = 'for f := iter.ReadObject(); f != ""; f = iter.ReadObject() {'
READ_ARRAY_LOOP = "for el := iter.ReadArray(); el; el = iter.ReadArray() {"

# Use this map to implement a type-checker for the next element / token in the stream
# e.g. we want do deserialize idShort, which is a (constrained)primitive type.
# Since we know, that idShort must be of type string, we can use it like this:
# if next != json.StringValue ... whatever is needed
_PRIMITIVE_JSON_TYPE_MAP = {
    intermediate.PrimitiveType.BOOL: "json.BoolValue",
    intermediate.PrimitiveType.STR: "json.StringValue",
    intermediate.PrimitiveType.INT: "json.NumberValue",
    intermediate.PrimitiveType.FLOAT: "json.NumberValue",
    intermediate.PrimitiveType.BYTEARRAY: "json.ArrayValue",
    "ARRAY": "json.ArrayValue",
    "STRING": "json.StringValue",
}

# Baisc Map to lookup the reader methods of the underlying iterator for a given primitive type
_PRIMITIVE_JSON_READER_METHOD_MAP = {
    intermediate.PrimitiveType.BOOL: "iter.ReadBool()",
    intermediate.PrimitiveType.STR: "iter.ReadString()",
    intermediate.PrimitiveType.INT: "iter.ReadNumber()",
    intermediate.PrimitiveType.FLOAT: "iter.ReadFloat64()",
    intermediate.PrimitiveType.BYTEARRAY: "iter.ReadString()",
}


def _get_primitive_json_writer_method(
    primitive: intermediate.PrimitiveType, val: str
) -> Stripped:
    if primitive is intermediate.PrimitiveType.BOOL:
        return f"stream.WriteBool({val})"
    elif primitive is intermediate.PrimitiveType.STR:
        return f"stream.WriteString({val})"
    elif primitive is intermediate.PrimitiveType.INT:
        return f"stream.WriteInt({val})"
    elif primitive is intermediate.PrimitiveType.FLOAT:
        return f"stream.WriteFloat64({val})"
    elif primitive is intermediate.PrimitiveType.BYTEARRAY:
        return f"stream.WriteString({val})"
    else:
        assert_never(primitive)


def _whats_next_boundary(expected_json_type: str) -> Stripped:
    # TODO (SG, 2021-12-28) next refers to a ValueType of type int, so returning got 5 (e.g. for ArrayValue) doesn't make sense here.
    # Check here, how to get the String since ValueType does not implement Stringer interface
    # https://github.com/json-iterator/go/blob/e6b9536d3649bda3e8842bb7e4fab489d79a97ea/iter.go
    return Stripped(
        textwrap.dedent(
            f"""\
            if next := iter.WhatIsNext(); next != {expected_json_type} {{
                iter.ReportError("unexpected-json-type", fmt.Sprintf("expected {expected_json_type}, got: %s", next))
            }}"""
        )
    )


def _generate_for_enum(
    enum: intermediate.Enumeration,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    name = golang_naming.enum_name(enum.name)

    writer = io.StringIO()

    # Unmarshal
    writer.write(f"func (e {name}) {UNMARSHAL_JSON_FUNC_SIG}")
    writer.write(_whats_next_boundary(_PRIMITIVE_JSON_TYPE_MAP["STRING"]))
    writer.write(
        f"""
            raw := iter.ReadString()
            if v, ok := {name}_value[raw]; !ok {{
                iter.ReportError("unknown-enum-value", fmt.Sprintf("%s is not a valid enum value", v))
            }} else {{
                e = v
            }}
        """
    )
    writer.write("} \n\n")

    # Marshal
    writer.write(f"func (e {name}) {MARSHAL_JSON_FUNC_SIG}")
    writer.write(
        f"""
            v := {name}_name[e]
            stream.WriteString(v)
        """
    )
    writer.write("}")

    return Stripped(writer.getvalue()), None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _generate_switch_property_unmarshaler(
    type_annotation: intermediate.TypeAnnotationUnion,
    prop_name: Identifier,
    json_prop_name: Identifier,
    is_required: bool,
    is_array=False,
) -> Tuple[
    Optional[Stripped], Optional[Error]
]:  # Even if its not needed for now, make the function return type a tuple, so that its consistent with others
    writer = io.StringIO()
    errors = []  # type: List[Error]

    if isinstance(type_annotation, intermediate.PrimitiveTypeAnnotation):
        type_reader = _PRIMITIVE_JSON_READER_METHOD_MAP[type_annotation.a_type]

        if type_reader is None:
            errors.append(
                Error(
                    type_annotation.parsed.node,
                    f"No reader for unmarshaling primitive type {type_annotation.a_type} defined.",
                )
            )
            return None, errors

        writer.write(
            _whats_next_boundary(_PRIMITIVE_JSON_TYPE_MAP[type_annotation.a_type])
        )
        writer.write("\n")
        writer.write(f"c.{prop_name} = {type_reader} \n")

        if not is_array and is_required:
            writer.write(f'isThere["{json_prop_name}"] = true \n')

    # generate the unmarshaler recursive
    # signature is e.g. Optional[Reference]
    elif isinstance(type_annotation, intermediate.OptionalTypeAnnotation):
        code, error = _generate_switch_property_unmarshaler(
            type_annotation=type_annotation.value,
            prop_name=prop_name,
            json_prop_name=json_prop_name,
            is_required=is_required,
        )
        if error is not None:
            errors.append(
                Error(
                    type_annotation.parsed.node,
                    f"Unmarshaler generation for property {prop_name} failed",
                )
            )
            return None, errors

        assert code is not None
        writer.write(code)

    elif isinstance(type_annotation, intermediate.OurTypeAnnotation):
        symbol = type_annotation.symbol
        # enumeration
        # enumerations (which are just types in our case) implement the unmarshaler interface
        # we can simply call it and assign the value
        if isinstance(symbol, intermediate.Enumeration):
            type_name = golang_naming.class_name(symbol.name)
            writer.write(
                f"""var myenum {type_name}
                    myenum.unmarshalJSON(iter) 
                    c.{prop_name} = &myenum \n"""
            )

            if not is_array and is_required:
                writer.write(f'isThere["{json_prop_name}"] = true \n')

        # constrainedPrimitive
        # 1. check, if the incoming value has correct type
        # 2. read the value from the iterator and assign it
        if isinstance(symbol, intermediate.ConstrainedPrimitive):
            type_reader = _PRIMITIVE_JSON_READER_METHOD_MAP[symbol.constrainee]

            if type_reader is None:
                Error(
                    type_annotation.parsed.node,
                    f"No reader for unmarshaling primitive type {type_annotation.a_type} defined.",
                )

            writer.write(
                _whats_next_boundary(_PRIMITIVE_JSON_TYPE_MAP[symbol.constrainee])
            )
            writer.write("\n")
            writer.write(f"c.{prop_name} = {type_reader} \n")

            if not is_array and is_required:
                writer.write(f'isThere["{json_prop_name}"] = true \n')

        # class
        # implement the unmarshaler Interface, so simply call it
        if isinstance(symbol, intermediate.Class):
            impl_name = golang_naming.class_name(symbol.name)
            writer.write(
                f"""myobj := &{impl_name}{{}}
                    myobj.unmarshalJSON(iter) \n"""
            )

            if is_array:
                writer.write(f"c.{prop_name} = append(c.{prop_name}, *myobj);")
            else:
                if is_required:
                    writer.write(f'isThere["{json_prop_name}"] = true \n')
                writer.write(f"c.{prop_name} = myobj;")

    elif isinstance(type_annotation, intermediate.RefTypeAnnotation):
        # TODO (SG, 2021-12-28) How to handle this?
        pass

    elif isinstance(type_annotation, intermediate.ListTypeAnnotation):
        writer.write(_whats_next_boundary(_PRIMITIVE_JSON_TYPE_MAP["ARRAY"]))
        writer.write("\n")
        writer.write(READ_ARRAY_LOOP)

        # generate the unmarshaller recursively
        code, error = _generate_switch_property_unmarshaler(
            type_annotation=type_annotation.items,
            prop_name=prop_name,
            json_prop_name=json_prop_name,
            is_array=True,
            is_required=is_required,
        )

        if error is not None:
            errors.append(
                Error(
                    type_annotation.parsed.node,
                    f"Unmarshaler generation for property {prop_name} failed",
                )
            )
            return None, errors

        assert code is not None

        writer.write(f"{code} }} \n")
        if is_required:
            writer.write(f'isThere["{json_prop_name}"] = true \n')

    else:
        assert_never(type_annotation)

    return writer.getvalue(), None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _generate_property_marshaler(
    type_annotation: intermediate.TypeAnnotationUnion,
    prop_name: Identifier,
    json_prop_name: Identifier,
    is_required: bool,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    writer = io.StringIO()
    errors = []  # type: List[Error]

    if isinstance(type_annotation, intermediate.PrimitiveTypeAnnotation):
        method_writer = _get_primitive_json_writer_method(
            type_annotation.a_type, f"c.{prop_name}"
        )
        if method_writer is None:
            errors.append(
                Error(
                    type_annotation.parsed.node,
                    f"No writer for marshaling primitive type {type_annotation.a_type}",
                )
            )
        writer.write(method_writer)

    elif isinstance(type_annotation, intermediate.OptionalTypeAnnotation):
        code, error = _generate_property_marshaler(
            type_annotation=type_annotation.value,
            prop_name=prop_name,
            json_prop_name=json_prop_name,
            is_required=is_required,
        )

        if error is not None:
            error.append(
                Error(
                    type_annotation.parsed.node,
                    f"Marshaler generation for property {prop_name} failed",
                )
            )
            return None, errors

        writer.write(code)

    elif isinstance(type_annotation, intermediate.OurTypeAnnotation):
        symbol = type_annotation.symbol

        # enumeration
        if isinstance(symbol, intermediate.Enumeration):
            writer.write(f" c.{prop_name}.marshalJSON(stream) \n")

        # constrainedPrimitive
        # simple; just take the value from the object and write it
        if isinstance(symbol, intermediate.ConstrainedPrimitive):
            method_writer = _get_primitive_json_writer_method(
                symbol.constrainee, f"c.{prop_name}"
            )
            writer.write(f"{method_writer} \n")

        # class
        if isinstance(symbol, intermediate.Class):
            writer.write(f"c.{prop_name}.marshalJSON(stream) \n")
            pass

    elif isinstance(type_annotation, intermediate.RefTypeAnnotation):
        pass

    elif isinstance(type_annotation, intermediate.ListTypeAnnotation):

        writer.write("stream.WriteArrayStart() \n")
        writer.write(f"for i, k := range c.{prop_name} {{ \n")
        writer.write(f"k.marshalJSON(stream) \n")
        writer.write(
            f"""if i < len(c.{prop_name}) - 1 {{
                stream.WriteMore()
            }}
            """
        )
        writer.write("}\n")
        writer.write("stream.WriteArrayEnd() \n")

        pass

    else:
        assert_never(type_annotation)

    return writer.getvalue(), None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _generate_for_class(
    clazz: intermediate.ConcreteClass,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    name = golang_naming.class_name(clazz.name)

    blocks = []  # type: List[Stripped]
    errors = []  # type: List[Error]

    # unmarshaler_writer is just a "wrapper" for the inner switch and verifier writer
    # that takes the result of the other writers and concatenates it
    unmarshaler_writer = io.StringIO()

    # verifier_writer writes the map for verifying required attributes
    # map has the following layout:
    #   isThere := map[string]bool {
    #       "idShort": false
    #   }
    # given property idShort is required
    verifier_writer = io.StringIO()
    verifier_writer.write("isThere := map[string]bool {\n")

    switch_writer = io.StringIO()

    # Unmarshaler starts here
    unmarshaler_writer.write(f"func (c *{name}) {UNMARSHAL_JSON_FUNC_SIG}")

    # In case of the AAS-Meta-Model we can be sure, that the first element in the byte-array
    # is always an object.
    switch_writer.write(READ_OBJECT_LOOP)
    switch_writer.write("switch f {")

    for prop in clazz.properties:
        prop_name = golang_naming.property_name(prop.name)
        json_prop_name = naming.json_property(prop.name)
        is_required = False

        # If the property is not optional, register it in the map
        if not isinstance(prop.type_annotation, intermediate.OptionalTypeAnnotation):
            is_required = True
            verifier_writer.write(f'"{json_prop_name}": false, \n')

        # NOTE (SG, 2021-12-28) We use the same approach like in the example c# lib:
        # One-Pass De/Serialization. We do hence not know the next property or element
        # in the stream. Therefore we read the next property-name from the stream and
        # call the aproperiate de/serialization operation on the respective property-name.
        #
        # e.g.
        # case "dataSpecifications": {
        #   if is primitive --> iter.ReadString() or whatever is needed
        #   if is not primitive:
        #       - for lists loop trough each element in the list
        #       - for non-lists: call the (un)marshalJSON method, since they have to implement the
        #         (Un)Marshaler interface
        # }
        switch_writer.write(f'case "{json_prop_name}":\n')
        code, error = _generate_switch_property_unmarshaler(
            type_annotation=prop.type_annotation,
            prop_name=prop_name,
            json_prop_name=json_prop_name,
            is_required=is_required,
        )

        if error is not None:
            errors.append(error)

        assert code is not None

        switch_writer.write(code)

    # throw an error if the property is unknown or does not belong to the object
    switch_writer.write(
        f"""default:
            iter.ReportError("unknown-property", fmt.Sprintf("%s is not a valid property in object {naming.json_property(clazz.name)}", f)) }}}}
            """
    )
    verifier_writer.write("}\n\n")

    unmarshaler_writer.write(verifier_writer.getvalue())
    unmarshaler_writer.write(switch_writer.getvalue())

    unmarshaler_writer.write(
        f"""
        for k, v := range isThere {{
            if !v {{
                iter.ReportError("Required property is missing", fmt.Sprintf("%s", k))
                break
            }}
        }}"""
    )
    unmarshaler_writer.write("}")
    blocks.append(unmarshaler_writer.getvalue())

    # Marshaler
    marshaler_writer = io.StringIO()
    marshaler_writer.write(f"func (c *{name}) {MARSHAL_JSON_FUNC_SIG}")
    marshaler_writer.write(f"stream.WriteObjectStart() \n")

    for i, prop in enumerate(clazz.properties):
        prop_name = golang_naming.property_name(prop.name)
        json_prop_name = naming.json_property(prop.name)
        is_required = False

        marshaler_writer.write(f'stream.WriteObjectField("{json_prop_name}") \n')

        if not isinstance(prop.type_annotation, intermediate.OptionalTypeAnnotation):
            is_required = True

        code, error = _generate_property_marshaler(
            type_annotation=prop.type_annotation,
            prop_name=prop_name,
            json_prop_name=json_prop_name,
            is_required=is_required,
        )

        if error is not None:
            errors.append(error)

        assert code is not None

        if i > 0 and i < len(clazz.properties):
            marshaler_writer.write(f"stream.WriteMore() \n\n")

        marshaler_writer.write(code)

    marshaler_writer.write(f"\n\nstream.WriteObjectEnd() \n")
    marshaler_writer.write("}")
    blocks.append(marshaler_writer.getvalue())

    return Stripped("\n\n".join(blocks)), None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
@ensure(
    lambda result: not (result[0] is not None) or result[0].endswith("\n"),
    "Trailing newline mandatory for valid end-of-files",
)
def generate(
    symbol_table: intermediate.SymbolTable,
    package_name: Stripped,
    spec_impls: specific_implementations.SpecificImplementations,
) -> Tuple[Optional[str], Optional[List[Error]]]:
    errors = []  # type: List[Error]
    blocks = [
        golang_common.WARNING,
        Stripped(f"package {package_name}"),
        Stripped(
            f"""import (
                        "io"
                        "fmt"

	                    json "github.com/json-iterator/go"
                    )"""
        ),
    ]

    jsonization_key = specific_implementations.ImplementationKey(
        f"Jsonization/interface.txt"
    )
    jsonization_text = spec_impls.get(jsonization_key, None)
    if jsonization_text is None:
        return None, errors.append(
            Error(None, f"The jsonization interface snippet is missing")
        )

    blocks.append(Stripped(jsonization_text))

    for symbol in symbol_table.symbols:
        code = None  # type: Optional[Stripped]
        error = None  # type: Optional[Error]

        if isinstance(symbol, intermediate.Enumeration):
            code, error = _generate_for_enum(symbol)
        elif isinstance(symbol, intermediate.ConstrainedPrimitive):
            continue
        elif isinstance(symbol, intermediate.Class):
            code, error = _generate_for_class(symbol)

        # NOTE (SG, 2021-12-28) we do not handle interfaces for the moment

        else:
            assert_never(symbol)

        assert (code is not None) ^ (error is not None)
        if error is not None:
            errors.append(error)
        else:
            assert code is not None
            blocks.append(code)

    if len(errors) > 0:
        return None, errors

    out = io.StringIO()
    for i, b in enumerate(blocks):
        if i > 0:
            out.write("\n\n")
        out.write(b)

    out.write("\n")
    return out.getvalue(), None
