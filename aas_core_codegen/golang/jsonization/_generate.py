import io
from re import T
import struct
import textwrap
from icontract import ensure
from typing import Tuple, Optional, List

from aas_core_codegen import intermediate, naming, specific_implementations
from aas_core_codegen import golang
from aas_core_codegen.golang import common as golang_common, naming as golang_naming
from aas_core_codegen.common import Error, Identifier, Stripped, assert_never


_UNMARSHAL_JSON_FUNC_SIG = "unmarshalJSON(iter *json.Iterator)"
_MARSHAL_JSON_FUNC_SIG = "marshalJSON(stream *json.Stream)"


_PRIMITIVE_JSON_TYPE_MAP = {
    intermediate.PrimitiveType.BOOL: "json.BoolValue",
    intermediate.PrimitiveType.STR: "json.StringValue",
    intermediate.PrimitiveType.INT: "json.NumberValue",
    intermediate.PrimitiveType.FLOAT: "json.NumberValue",
    intermediate.PrimitiveType.BYTEARRAY: "json.ArrayValue",
    "ARRAY": "json.ArrayValue",
    "STRING": "json.StringValue",
}

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
    return Stripped(
        textwrap.dedent(
            f"""if next := iter.WhatIsNext(); next != {expected_json_type} {{
                    iter.ReportError("unexpected-json-type", fmt.Sprintf("expected {expected_json_type}, got: %s", next))
            }}"""
        )
    )


def _generate_for_enum(
    enum: intermediate.Enumeration,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    name = golang_naming.enum_name(enum.name)

    writer = io.StringIO()

    # Unmarshal (Function)
    # Start
    writer.write(
        Stripped(
            textwrap.dedent(
                f"""// unmarshalJSON implements the Unmarshaler interface for {name}
        func (e {name}) {_UNMARSHAL_JSON_FUNC_SIG} {{
            raw := iter.ReadString()
            if v, ok := {name}_value[raw]; !ok {{
                iter.ReportError("unknown-enum-value", fmt.Sprintf("%s is not a valid enum value", raw))
            }} else {{
                e = v
            }}
        }}"""
            )
        )
    )
    # End
    writer.write("\n\n")

    # Marshal
    # Start
    writer.write(
        Stripped(
            textwrap.dedent(
                f"""// marshalJSON implements the Marshaler interface for {name}
        func (e {name}) {_MARSHAL_JSON_FUNC_SIG} {{
            stream.WriteString({name}_name[e])            
        }}"""
            )
        )
    )

    return Stripped(writer.getvalue()), None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _generate_switch_property_unmarshaler(
    type_annotation: intermediate.TypeAnnotationUnion,
    prop_name: Identifier,
    json_prop_name: Identifier,
    is_required: bool,
    is_array=False,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    writer = io.StringIO()
    errors = []  # type: List[Error]

    if isinstance(type_annotation, intermediate.PrimitiveTypeAnnotation):
        # primitive type annotation
        # 1. check, if the incoming value has correct type
        # 2. read the value from the iterator and assign it
        type = type_annotation.a_type
        type_reader = _PRIMITIVE_JSON_READER_METHOD_MAP[type]
        if type_reader is None:
            errors.append(
                Error(
                    type_annotation.parsed.node,
                    f"No reader for unmarshaling primitive type {type} defined.",
                )
            )
            return None, errors

        writer.write(_whats_next_boundary(_PRIMITIVE_JSON_TYPE_MAP[type]))
        writer.write("\n")
        if is_required:
            writer.write(f"c.{prop_name} = {type_reader} \n")
            if not is_array:
                writer.write(f'isThere["{json_prop_name}"] = true \n')

        else:
            writer.write(f"val := {type_reader}\n")
            writer.write(f"c.{prop_name} = &val \n")

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
        # enumeration type annotation
        # 1. init the enum with zero value
        # 2. call the receiver method on the enum
        # 3. assign the enum to the struct property
        if isinstance(symbol, intermediate.Enumeration):
            type_name = golang_naming.struct_name(symbol.name)
            writer.write(
                f"""var myenum {type_name}
                    myenum.unmarshalJSON(iter) 
                """
            )
            if is_required:
                writer.write(f"c.{prop_name} = myenum \n")
                if not is_array:
                    writer.write(f'isThere["{json_prop_name}"] = true \n')

            else:
                writer.write(f"c.{prop_name} = &myenum \n")

        # constrained primitive
        # 1. check, if the incoming value has correct type
        # 2. read the value from the iterator and assign it
        if isinstance(symbol, intermediate.ConstrainedPrimitive):
            type = symbol.constrainee
            type_reader = _PRIMITIVE_JSON_READER_METHOD_MAP[type]

            if type_reader is None:
                Error(
                    type_annotation.parsed.node,
                    f"No reader for unmarshaling primitive type {type} defined.",
                )

            writer.write(_whats_next_boundary(_PRIMITIVE_JSON_TYPE_MAP[type]))
            writer.write("\n")
            if is_required:
                writer.write(f"c.{prop_name} = {type_reader} \n")
                if not is_array:
                    writer.write(f'isThere["{json_prop_name}"] = true \n')

            else:
                writer.write(f"val := {type_reader}\n")
                writer.write(f"c.{prop_name} = &val \n")
        # class
        # 1. check if the class is abstract
        # 1.1 if is abstract
        if isinstance(symbol, intermediate.Class):
            name = golang_naming.struct_name(symbol.name)
            if symbol.interface:
                name = f"{golang_naming.struct_name(symbol.interface.name)}Data"

            writer.write(
                f"""myobj := &{name}{{}}
                    myobj.unmarshalJSON(iter)
                """
            )

            if is_array:
                writer.write(f"c.{prop_name} = append(c.{prop_name}, myobj); \n")
            else:
                if is_required:
                    writer.write(f'isThere["{json_prop_name}"] = true \n')

                writer.write(f"c.{prop_name} = myobj;")

    elif isinstance(type_annotation, intermediate.RefTypeAnnotation):
        # TODO (SG, 2021-12-28) How to handle this?
        pass

    elif isinstance(type_annotation, intermediate.ListTypeAnnotation):
        writer.write(
            f""" \
            // loop through every element in the array and unmarshal it
            {_whats_next_boundary(_PRIMITIVE_JSON_TYPE_MAP["ARRAY"])}
            for el := iter.ReadArray(); el; el = iter.ReadArray() {{
        """
        )

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
        prop = f"*c.{prop_name}"
        if is_required:
            prop = f"c.{prop_name}"
        method_writer = _get_primitive_json_writer_method(type_annotation.a_type, prop)
        if method_writer is None:
            errors.append(
                Error(
                    type_annotation.parsed.node,
                    f"No writer for marshaling primitive type {type_annotation.a_type}",
                )
            )
        writer.write(f"{method_writer}")
        writer.write("\n")

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
            writer.write(f"c.{prop_name}.marshalJSON(stream) \n")

        # constrainedPrimitive
        # simple; just take the value from the object and write it
        if isinstance(symbol, intermediate.ConstrainedPrimitive):
            prop = f"*c.{prop_name}"
            if is_required:
                prop = f"c.{prop_name}"
            method_writer = _get_primitive_json_writer_method(symbol.constrainee, prop)
            writer.write(f"{method_writer}")
            writer.write("\n")

        # class
        if isinstance(symbol, intermediate.Class):
            writer.write(f"c.{prop_name}.marshalJSON(stream) \n")

    elif isinstance(type_annotation, intermediate.RefTypeAnnotation):
        pass

    elif isinstance(type_annotation, intermediate.ListTypeAnnotation):
        code = "k.marshalJSON(stream)"

        if isinstance(
            type_annotation.items, intermediate.PrimitiveTypeAnnotation
        ) or isinstance(type_annotation.items, intermediate.ConstrainedPrimitive):
            code = _get_primitive_json_writer_method(type_annotation.items.a_type, "k")

        writer.write(
            textwrap.dedent(
                f"""// loop through every element in the slice and write it to the stream
                    stream.WriteArrayStart()
                    for i, k := range c.{prop_name} {{
                        {code}
                        if i < len(c.{prop_name}) - 1 {{
                            stream.WriteMore()
                        }}
                    }}
                    stream.WriteArrayEnd()
                """
            )
        )

    else:
        assert_never(type_annotation)

    return writer.getvalue(), None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _generate_for_interface(
    interface: intermediate.Interface,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    """Generates the Go code for unmarshalling and marshalling generic elements of the meta-model"""
    base_prop_names = []  # Type: List[Identifier]

    name = f"{golang_naming.struct_name(interface.name)}Data"
    blocks = []  # type: List[Stripped]
    errors = []  # type: List[Error]

    # unmarshaler_writer is just a "wrapper" for the inner switch writer
    # that takes the result of the other writers and concatenates it
    unmarshaler_writer = io.StringIO()
    temp_object_writer = io.StringIO()
    switch_writer = io.StringIO()
    type_checker_writer = io.StringIO()

    unmarshaler_writer.write(
        f"""// unmarshalJSON implements the Unmarshaler interface for {name}
    func (d *{name}) {_UNMARSHAL_JSON_FUNC_SIG} {{
    """
    )

    switch_writer.write(
        """// iterate through all provided object properties and switch on property name
            for f := iter.ReadObject(); f != ""; f = iter.ReadObject() {
            switch f {"""
    )

    # create a temporary object with all
    #    - base properties of the interface
    #    - properties which are added by the concrete implementation
    #
    # c := struct {
    #   // base properties
    #   ... rest properties
    # }{}
    #
    temp_object_writer.write("c := struct { \n")
    temp_object_writer.write("// Shared Properties \n")

    # iterate through all the properties of the interface
    # 1. add the properties to the temp object
    # 2. write them to the switch writer
    for prop in interface.properties:

        base_prop_names.append(prop.name)
        prop_name = golang_naming.property_name(prop.name)
        prop_type = golang_common.generate_type(type_annotation=prop.type_annotation)

        json_prop_name = naming.json_property(prop.name)
        temp_object_writer.write(f"{prop_name} {prop_type} \n")

        switch_writer.write(f'case "{json_prop_name}":')
        code, error = _generate_switch_property_unmarshaler(
            type_annotation=prop.type_annotation,
            prop_name=prop_name,
            json_prop_name=json_prop_name,
            is_required=False,
        )
        if error is not None:
            errors.append(error)
        else:
            assert code is not None
            switch_writer.write(code)

    prop_cache = dict()  # Type: Dict[Identifier: Dict[]]

    # iterate through all the implementers
    for impl in interface.implementers:
        # iterate through all the props of the implementer
        for prop in impl.properties:
            # check if the property is inherited from the interface
            if prop.name not in base_prop_names:
                # check whether the
                if prop.name not in prop_cache.keys():
                    prop_name = golang_naming.property_name(prop.name)
                    prop_type = golang_common.generate_type(
                        type_annotation=prop.type_annotation, enforce_pointer=True
                    )
                    json_prop_name = naming.json_property(prop.name)

                    d = dict()
                    d["prop_name"] = prop_name
                    d["prop_type"] = prop_type
                    d["impls"] = [impl.name]

                    prop_cache[prop.name] = d

                    switch_writer.write(f'case"{json_prop_name}": \n')

                    code, error = _generate_switch_property_unmarshaler(
                        type_annotation=prop.type_annotation,
                        prop_name=prop_name,
                        json_prop_name=json_prop_name,
                        is_required=False,
                    )

                    if error is not None:
                        errors.append(error)
                    assert code is not None
                    switch_writer.write(code)
                else:
                    d = prop_cache[prop.name]
                    impls = d["impls"]
                    impls.append(impl.name)
                    d["impls"] = impls
                    prop_cache[prop.name] = d

    for val in prop_cache.values():
        n = val["prop_name"]
        t = val["prop_type"]
        i = "{}".format(
            " + ".join(golang_naming.struct_name(part) for part in val["impls"])
        )
        temp_object_writer.write(f"// Used in {i} \n")
        temp_object_writer.write(f"{n} {t} \n")

    temp_object_writer.write("}{}\n")

    switch_writer.write(
        f"""default:
            iter.ReportError("unknown-property", fmt.Sprintf("%s is not a valid property in object", f))
            """
    )

    # End Switch
    switch_writer.write("}")

    unmarshaler_writer.write(temp_object_writer.getvalue())
    unmarshaler_writer.write(switch_writer.getvalue())
    unmarshaler_writer.write("\n\n")

    for i, impl in enumerate(interface.implementers):
        if len(impl.properties) > 0:
            struct_name = golang_naming.struct_name(impl.name)

            if_stmt_written = False
            for j, prop in enumerate(impl.properties):
                prop_name = golang_naming.property_name(prop.name)
                if prop.name not in base_prop_names:
                    if if_stmt_written == False:
                        if i == 0:
                            type_checker_writer.write(
                                f"// Check if element is of type {struct_name} \n"
                            )
                            type_checker_writer.write("if ")
                        else:
                            type_checker_writer.write("else if ")
                            type_checker_writer.write(
                                f"// Check if element is of type {struct_name} \n"
                            )

                        if_stmt_written = True

                    type_checker_writer.write(f"c.{prop_name} != nil ")
                    if j == len(impl.properties) - 1:
                        type_checker_writer.write("{ \n")
                        type_checker_writer.write(
                            f"""// Construct {struct_name}
                                var obj *{struct_name}
                            """
                        )
                        for prop in impl.properties:
                            prop_name = golang_naming.property_name(prop.name)
                            assignement = f"c.{prop_name}"
                            if not isinstance(
                                prop.type_annotation,
                                intermediate.OptionalTypeAnnotation,
                            ) and not isinstance(
                                prop.type_annotation, intermediate.ListTypeAnnotation
                            ):
                                assignement = f"*c.{prop_name}"

                            else:
                                type_checker_writer.write(
                                    f"obj.{prop_name} = {assignement} \n"
                                )
                        type_checker_writer.write(f"// Assign obj to {name} \n")
                        type_checker_writer.write(f"d.{struct_name} = obj")

                        type_checker_writer.write("}")
                    else:
                        type_checker_writer.write("&& ")

    unmarshaler_writer.write(type_checker_writer.getvalue())
    unmarshaler_writer.write("}}")
    blocks.append(unmarshaler_writer.getvalue())

    marshaler_writer = io.StringIO()
    # Marshal (Function)
    # Start
    marshaler_writer.write(
        f""" \
        // marshalJSON implements Marshaler interface for {name}
        func (d *{name}) {_MARSHAL_JSON_FUNC_SIG} {{
            stream.WriteObjectStart()"""
    )

    marshaler_writer.write("}")
    blocks.append(marshaler_writer.getvalue())

    return Stripped("\n\n".join(blocks)), None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _generate_for_class(
    clazz: intermediate.ConcreteClass,
) -> Tuple[Optional[Stripped], Optional[Error]]:
    name = golang_naming.struct_name(clazz.name)
    blocks = []  # type: List[Stripped]
    errors = []  # type: List[Error]

    # unmarshaler_writer is just a "wrapper" for the inner switch and verifier writer
    # that takes the result of the other writers and concatenates it
    unmarshaler_writer = io.StringIO()

    verifier_writer = io.StringIO()
    # Open verifier map
    verifier_writer.write("isThere := map[string]bool { \n")

    switch_writer = io.StringIO()

    # Unmarshal (Function)
    # Start
    unmarshaler_writer.write(
        f"""// unmarshalJSON implements the Unmarshaler interface for {name}
        func (c *{name}) {_UNMARSHAL_JSON_FUNC_SIG} {{
        """
    )

    # Start Switch
    switch_writer.write(
        """// iterate through all provided object properties and switch on property name
            for f := iter.ReadObject(); f != ""; f = iter.ReadObject() {
            switch f {"""
    )
    for prop in clazz.properties:
        prop_name = golang_naming.property_name(prop.name)
        json_prop_name = naming.json_property(prop.name)
        is_required = False
        # property is not optional? write it to the verifier
        if not isinstance(prop.type_annotation, intermediate.OptionalTypeAnnotation):
            is_required = True
            verifier_writer.write(f'"{json_prop_name}": false, \n')

        switch_writer.write(f'case "{json_prop_name}": \n')

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
            iter.ReportError("unknown-property", fmt.Sprintf("%s is not a valid property in object {naming.json_property(clazz.name)}", f))
            """
    )
    # End Switch
    switch_writer.write("}}")

    # Close Verifier Map
    verifier_writer.write("} \n")

    # Write the verifier value at the very top
    unmarshaler_writer.write(verifier_writer.getvalue())
    # Append switch values
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

    marshaler_writer = io.StringIO()
    # Marshal (Function)
    # Start
    marshaler_writer.write(
        f""" \
        // marshalJSON implements Marshaler interface for {name}
        func (c *{name}) {_MARSHAL_JSON_FUNC_SIG} {{
            stream.WriteObjectStart()

        """
    )

    for i, prop in enumerate(clazz.properties):
        prop_name = golang_naming.property_name(prop.name)
        json_prop_name = naming.json_property(prop.name)
        is_required = False

        if not isinstance(prop.type_annotation, intermediate.OptionalTypeAnnotation):
            is_required = True

        if not is_required:
            marshaler_writer.write(f"if c.{prop_name} != nil {{\n")
        marshaler_writer.write(f'stream.WriteObjectField("{json_prop_name}") \n')

        code, error = _generate_property_marshaler(
            type_annotation=prop.type_annotation,
            prop_name=prop_name,
            json_prop_name=json_prop_name,
            is_required=is_required,
        )

        if error is not None:
            errors.append(error)

        assert code is not None

        marshaler_writer.write(code)

        if i > 0 and i < len(clazz.properties) - 1:
            marshaler_writer.write(f"stream.WriteMore()")

        if not is_required:
            marshaler_writer.write("}\n\n")

        marshaler_writer.write("\n\n")

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

    abstract_usages = golang_common.find_abstract_class_usages(
        symbol_table=symbol_table
    )

    errors = []  # type: List[Error]
    blocks = [
        golang_common.WARNING,
        f"package {package_name}",
        f"""import (
                        "io"
                        "fmt"
                        "reflect"

	                    json "github.com/json-iterator/go"
                    )""",
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

    for symbol in golang_common.over_enumerations_classes_and_interfaces(
        symbol_table=symbol_table
    ):
        code = None  # type: Optional[Stripped]
        error = None  # type: Optional[Error]

        if isinstance(symbol, intermediate.Enumeration):
            code, error = _generate_for_enum(symbol)

        elif isinstance(symbol, intermediate.ConstrainedPrimitive):
            continue

        elif isinstance(symbol, intermediate.Class):
            code, error = _generate_for_class(symbol)

        elif isinstance(symbol, intermediate.Interface):
            if symbol.name in abstract_usages:
                code, error = _generate_for_interface(symbol)
            else:
                code = ""

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
