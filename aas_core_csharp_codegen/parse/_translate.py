"""Translate the abstract syntax tree of the meta-model into parsed structures."""

import ast
import collections
import textwrap
from typing import List, Any, Optional, cast, Type, Tuple, Union

import asttokens
from icontract import ensure, require

from aas_core_csharp_codegen.common import (
    Error,
    Identifier,
    IDENTIFIER_RE,
    LinenoColumner,
    assert_never,
)
from aas_core_csharp_codegen.parse._types import (
    AbstractEntity,
    Argument,
    AtomicTypeAnnotation,
    ConcreteEntity,
    Contract,
    Contracts,
    Default,
    Entity,
    Enumeration,
    EnumerationLiteral,
    final_in_type_annotation,
    is_string_expr,
    Method,
    Property,
    SelfTypeAnnotation,
    Snapshot,
    SubscriptedTypeAnnotation,
    Symbol,
    SymbolTable,
    TypeAnnotation,
    UnverifiedSymbolTable,
)


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def source_to_atok(
    source: str,
) -> Tuple[Optional[asttokens.ASTTokens], Optional[Exception]]:
    """
    Parse the Python code.

    :param source: Python code as text
    :return: parsed module or error, if any
    """
    try:
        atok = asttokens.ASTTokens(source, parse=True)
    except Exception as error:
        return None, error

    return atok, None


class _ExpectedImportsVisitor(ast.NodeVisitor):
    # pylint: disable=invalid-name
    # pylint: disable=missing-docstring

    def __init__(self) -> None:
        self.errors = []  # type: List[Error]

    def visit_Import(self, node: ast.Import) -> Any:
        self.errors.append(
            Error(
                node=node,
                message=f"Unexpected ``import ...``. "
                f"Only ``from ... import...`` statements are expected.",
            )
        )

    _EXPECTED_NAME_FROM_MODULE = collections.OrderedDict(
        [
            ("Enum", "enum"),
            ("Final", "typing"),
            ("List", "typing"),
            ("Optional", "typing"),
            ("require", "icontract"),
            ("ensure", "icontract"),
            ("DBC", "icontract"),
            ("abstract", "aas_core3_meta.marker"),
            ("implementation_specific", "aas_core3_meta.marker"),
            ("comment", "aas_core3_meta.marker"),
            ("is_IRI", "aas_core3_meta.pattern"),
            ("is_IRDI", "aas_core3_meta.pattern"),
            ("is_id_short", "aas_core3_meta.pattern"),
        ]
    )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        for name in node.names:
            assert isinstance(name, ast.alias)
            if name.asname is not None:
                self.errors.append(
                    Error(
                        node=name,
                        message=f"Unexpected ``from ... import ... as ...``. "
                        f"Only ``from ... import...`` statements are expected.",
                    )
                )
            else:
                if name.name not in self._EXPECTED_NAME_FROM_MODULE:
                    self.errors.append(
                        Error(
                            node=name,
                            message=f"Unexpected import of a name {name.name!r}.",
                        )
                    )

                else:
                    expected_module = self._EXPECTED_NAME_FROM_MODULE[name.name]
                    if expected_module != node.module:
                        self.errors.append(
                            Error(
                                node=name,
                                message=f"Expected to import {name.name!r} "
                                f"from the module {expected_module}, "
                                f"but it is imported from {node.module}.",
                            )
                        )


def check_expected_imports(atok: asttokens.ASTTokens) -> List[str]:
    """
    Check that only expected imports are stated in the module.

    This is important so that we can parse type annotations and inheritances.

    Return errors, if any.
    """
    visitor = _ExpectedImportsVisitor()
    visitor.visit(atok.tree)

    if len(visitor.errors) == 0:
        return []

    lineno_columner = LinenoColumner(atok=atok)
    return [lineno_columner.error_message(error) for error in visitor.errors]


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _enum_to_symbol(
    node: ast.ClassDef, atok: asttokens.ASTTokens
) -> Tuple[Optional[Enumeration], Optional[Error]]:
    """Interpret a class which defines an enumeration."""
    if len(node.body) == 0:
        return (
            Enumeration(
                name=Identifier(node.name), literals=[], description=None, node=node
            ),
            None,
        )

    enumeration_literals = []  # type: List[EnumerationLiteral]

    description = None  # type: Optional[str]

    cursor = 0
    while cursor < len(node.body):
        old_cursor = cursor

        body_node = node.body[cursor]  # type: ast.AST

        if cursor == 0 and is_string_expr(body_node):
            assert isinstance(body_node, ast.Expr)
            description = _string_expr_to_text(body_node)
            cursor += 1

        elif isinstance(body_node, ast.Pass):
            cursor += 1

        elif isinstance(body_node, ast.Assign):
            assign = body_node

            if len(assign.targets) != 1:
                return (
                    None,
                    Error(
                        node=assign,
                        message=f"Expected a single target in the assignment, "
                        f"but got: {len(assign.targets)}",
                    ),
                )

            if not isinstance(assign.targets[0], ast.Name):
                return (
                    None,
                    Error(
                        node=assign.targets[0],
                        message=f"Expected a name as a target of the assignment, "
                        f"but got: {assign.targets[0]}",
                    ),
                )

            if not isinstance(assign.value, ast.Constant):
                return (
                    None,
                    Error(
                        node=assign.value,
                        message=f"Expected a constant in the enumeration assignment, "
                        f"but got: {atok.get_text(assign.value)}",
                    ),
                )

            if not isinstance(assign.value.value, str):
                return (
                    None,
                    Error(
                        node=assign.value,
                        message=f"Expected a string literal in the enumeration, "
                        f"but got: {assign.value.value}",
                    ),
                )

            literal_name = Identifier(assign.targets[0].id)
            literal_value = assign.value.value

            literal_description = None  # type: Optional[str]
            next_expr = node.body[cursor + 1] if cursor < len(node.body) - 1 else None

            if next_expr is not None and is_string_expr(next_expr):
                assert isinstance(next_expr, ast.Expr)
                literal_description = _string_expr_to_text(next_expr)
                cursor += 1

            enumeration_literals.append(
                EnumerationLiteral(
                    name=literal_name,
                    value=literal_value,
                    description=literal_description,
                    node=assign,
                )
            )

            cursor += 1

        else:
            return (
                None,
                Error(
                    node=node.body[cursor],
                    message=f"Expected either a docstring or an assignment "
                    f"in an enumeration, "
                    f"but got: {atok.get_text(node.body[cursor])}",
                ),
            )

        assert cursor > old_cursor, f"Loop invariant: {cursor=}, {old_cursor=}"

    return (
        Enumeration(
            name=Identifier(node.name),
            literals=enumeration_literals,
            description=description,
            node=node,
        ),
        None,
    )


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _type_annotation(
    node: ast.AST, atok: asttokens.ASTTokens
) -> Tuple[Optional[TypeAnnotation], Optional[Error]]:
    """Parse the type annotation."""
    if isinstance(node, ast.Name):
        if node.id == "Final":
            return (
                None,
                Error(
                    node,
                    "The type annotation is expected with subscript(s), "
                    "but got none: Final",
                ),
            )

        return AtomicTypeAnnotation(identifier=Identifier(node.id)), None

    elif isinstance(node, ast.Constant):
        if not isinstance(node.value, str):
            return (
                None,
                Error(
                    node=node.value,
                    message=f"Expected a string literal "
                    f"if the type annotation is given as a constant, "
                    f"but got: "
                    f"{node.value!r} (as {type(node.value)})",
                ),
            )

        return AtomicTypeAnnotation(identifier=Identifier(node.value)), None

    elif isinstance(node, ast.Subscript):
        if not isinstance(node.value, ast.Name):
            return (
                None,
                Error(
                    node=node.value,
                    message=f"Expected a name to define "
                    f"a subscripted type annotation,"
                    f"but got: {atok.get_text(node.value)}",
                ),
            )

        if isinstance(node.slice, ast.Index):
            subscripts = []  # type: List[TypeAnnotation]

            if isinstance(node.slice.value, ast.Tuple):
                for elt in node.slice.value.elts:
                    subscript_annotation, error = _type_annotation(node=elt, atok=atok)
                    if error is not None:
                        return None, error

                    assert subscript_annotation is not None

                    subscripts.append(subscript_annotation)

            elif isinstance(node.slice.value, (ast.Name, ast.Subscript, ast.Constant)):
                subscript_annotation, error = _type_annotation(
                    node=node.slice.value, atok=atok
                )
                if error is not None:
                    return None, error

                assert subscript_annotation is not None

                subscripts.append(subscript_annotation)

            else:
                return (
                    None,
                    Error(
                        node.slice.value,
                        f"Expected a tuple, a name, a subscript or a string literal "
                        f"for a subscripted type annotation, "
                        f"but got: {atok.get_text(node.slice.value)}",
                    ),
                )

            return (
                SubscriptedTypeAnnotation(
                    identifier=Identifier(node.value.id), subscripts=subscripts
                ),
                None,
            )

        else:
            return (
                None,
                Error(
                    node=node.slice,
                    message=f"Expected an index to define "
                    f"a subscripted type annotation, "
                    f"but got: {atok.get_text(node.slice)}",
                ),
            )
    else:
        return (
            None,
            Error(
                node,
                f"Expected either atomic type annotation (as name or string literal) "
                f"or a subscripted one (as a subscript), "
                f"but got: {atok.get_text(node)} (as {type(node)})",
            ),
        )


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _ann_assign_to_property(
    node: ast.AnnAssign, description: Optional[str], atok: asttokens.ASTTokens
) -> Tuple[Optional[Property], Optional[Error]]:
    if not isinstance(node.target, ast.Name):
        return (
            None,
            Error(
                node.target,
                f"Expected property target to be a name, "
                f"but got: {atok.get_text(node.target)}",
            ),
        )

    if not node.simple:
        return (
            None,
            Error(
                node.target,
                f"Expected a property with a simple target " f"(no parentheses!)",
            ),
        )

    if node.annotation is None:
        return (
            None,
            Error(node.target, f"Expected property to be annotated with a type"),
        )

    type_annotation, error = _type_annotation(node=node.annotation, atok=atok)
    if error is not None:
        return None, error

    assert type_annotation is not None

    if node.value is not None:
        return (
            None,
            Error(node.value, f"Unexpected assignment of a value to a property"),
        )

    is_readonly = False
    if (
        isinstance(type_annotation, SubscriptedTypeAnnotation)
        and type_annotation.identifier == "Final"
    ):
        if len(type_annotation.subscripts) != 1:
            return (
                None,
                Error(
                    node.annotation,
                    f"Expected a single subscript for Final type, "
                    f"but got {len(type_annotation.subscripts)}",
                ),
            )

        type_annotation = type_annotation.subscripts[0]
        is_readonly = True

        if final_in_type_annotation(type_annotation=type_annotation):
            return (
                None,
                Error(
                    node.annotation,
                    f"Unexpected nested Final type qualifier: "
                    f"{atok.get_text(node.annotation)}",
                ),
            )

    return (
        Property(
            name=Identifier(node.target.id),
            type_annotation=type_annotation,
            description=description,
            is_readonly=is_readonly,
            node=node,
        ),
        None,
    )


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _args_to_arguments(
    node: ast.arguments, atok: asttokens.ASTTokens
) -> Tuple[Optional[List[Argument]], Optional[Error]]:
    """Parse arguments of a method."""
    if hasattr(node, "posonlyargs") and len(node.posonlyargs) > 0:
        return None, Error(node, f"Unexpected positional-only arguments")

    if node.vararg is not None or node.kwarg is not None:
        return None, Error(node, f"Unexpected variable arguments")

    if len(node.kwonlyargs) > 0:
        return None, Error(node, f"Unexpected keyword-only arguments")

    assert len(node.kw_defaults) == 0, (
        "No keyword-only arguments implies "
        "there should be no defaults "
        "for keyword-only arguments either."
    )

    if len(node.args) == 0:
        return None, Error(node, f"Unexpected no arguments")

    arguments = []  # type: List[Argument]

    # region ``self``

    if node.args[0].arg != "self":
        return None, Error(node, f"Unexpected no ``self`` in arguments")

    if node.args[0].annotation is not None:
        return (
            None,
            Error(
                node.args[0],
                f"Unexpected type annotation for the method argument ``self``",
            ),
        )

    if len(node.defaults) == len(node.args):
        return (
            None,
            Error(
                node.args[0],
                f"Unexpected default value for the method argument ``self``",
            ),
        )

    arguments.append(
        Argument(
            name=Identifier("self"),
            type_annotation=SelfTypeAnnotation(),
            default=None,
            node=node.args[0],
        )
    )

    # endregion

    # region Non-self arguments

    for i in range(1, len(node.args)):
        arg_node = node.args[i]

        # region Type annotation
        if arg_node.annotation is None:
            return (
                None,
                Error(
                    arg_node,
                    f"Unexpected method argument without a type annotation: "
                    f"{arg_node.arg}",
                ),
            )

        type_annotation, error = _type_annotation(node=arg_node.annotation, atok=atok)
        if error is not None:
            return (
                None,
                Error(
                    arg_node,
                    f"Failed to parse the type annotation "
                    f"of the method argument {arg_node.arg}: "
                    f"{atok.get_text(arg_node.annotation)}",
                    underlying=[error],
                ),
            )

        assert type_annotation is not None

        if final_in_type_annotation(type_annotation=type_annotation):
            return (
                None,
                Error(
                    arg_node,
                    f"Unexpected ``Final`` in the type annotation "
                    f"of the method argument {arg_node.arg}: "
                    f"{atok.get_text(arg_node.annotation)}",
                ),
            )

        assert type_annotation is not None
        # endregion

        # region Default
        default = None  # type: Optional[Default]
        offset = len(node.args) - len(node.defaults)
        if i >= offset:
            default_node = node.defaults[i - offset]
            if not isinstance(default_node, ast.Constant):
                return (
                    None,
                    Error(
                        default_node,
                        (
                            f"Expected a constant as a default value, "
                            f"but got: {atok.get_text(default_node)}"
                        ),
                    ),
                )

            if not (
                default_node.value is None
                or isinstance(default_node.value, (bool, int, float, str))
            ):
                return (
                    None,
                    Error(
                        default_node,
                        (
                            f"Expected a constant of type int, float, bool, "
                            f"or a None literal as a default value, "
                            f"but got: {atok.get_text(default_node)}"
                        ),
                    ),
                )

            assert default_node.value is None or isinstance(
                default_node.value, (bool, int, float, str)
            )
            default = Default(value=default_node.value)

        # endregion

        arguments.append(
            Argument(
                name=Identifier(arg_node.arg),
                type_annotation=type_annotation,
                default=default,
                node=arg_node,
            )
        )

    # endregion

    return arguments, None


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _parse_contract_condition(
    node: ast.Call, atok: asttokens.ASTTokens
) -> Tuple[Optional[Contract], Optional[Error]]:
    """Parse the contract decorator."""
    condition_node = None  # type: Optional[ast.AST]
    description_node = None  # type: Optional[ast.AST]

    if len(node.args) >= 1:
        condition_node = node.args[0]

    if len(node.args) >= 2:
        description_node = node.args[1]

    for keyword in node.keywords:
        if keyword.arg == "condition":
            condition_node = keyword.value

        elif keyword.arg == "description":
            description_node = keyword.value

        else:
            # We simply ignore to parse the argument.
            pass

    if condition_node is None:
        return (
            None,
            Error(node, "Expected the condition to be defined for a contract"),
        )

    if not isinstance(condition_node, ast.Lambda):
        return (
            None,
            Error(
                condition_node,
                f"Expected a lambda function as a contract condition, "
                f"but got: {atok.get_text(condition_node)}",
            ),
        )

    if description_node is not None and not (
        isinstance(description_node, ast.Constant)
        and isinstance(description_node.value, str)
    ):
        return (
            None,
            Error(
                description_node,
                f"Expected a string literal as a contract description, "
                f"but got: {atok.get_text(description_node)!r}",
            ),
        )

    return (
        Contract(
            args=[Identifier(arg.arg) for arg in condition_node.args.args],
            description=None if description_node is None else description_node.value,
            body=condition_node.body,
            condition_node=condition_node,
        ),
        None,
    )


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _parse_snapshot(
    node: ast.Call, atok: asttokens.ASTTokens
) -> Tuple[Optional[Snapshot], Optional[Error]]:
    """Parse the snapshot decorator."""
    capture_node = None  # type: Optional[ast.AST]
    name_node = None  # type: Optional[ast.AST]

    if len(node.args) >= 1:
        capture_node = node.args[0]

    if len(node.args) >= 2:
        name_node = node.args[1]

    for keyword in node.keywords:
        if keyword.arg == "capture":
            capture_node = keyword.value

        elif keyword.arg == "name":
            name_node = keyword.value

        else:
            # We simply ignore to parse the argument.
            pass

    if capture_node is None:
        return (None, Error(node, "Expected the capture to be defined for a snapshot"))

    if not isinstance(capture_node, ast.Lambda):
        return (
            None,
            Error(
                capture_node,
                f"Expected a lambda function as a capture of a snapshot, "
                f"but got: {atok.get_text(capture_node)}",
            ),
        )

    if name_node is not None and not (
        isinstance(name_node, ast.Constant) and isinstance(name_node.value, str)
    ):
        return (
            None,
            Error(
                name_node,
                f"Expected a string literal as a capture name, "
                f"but got: {atok.get_text(name_node)}",
            ),
        )

    if name_node is not None:
        name = name_node.value
    elif len(capture_node.args.args) == 1 and name_node is None:
        name = capture_node.args.args[0].arg
    else:
        return (
            None,
            Error(
                node,
                f"Expected the name of the snapshot to be defined, "
                f"but there was neither the single argument in the capture "
                f"nor explicit ``name`` given",
            ),
        )

    if not IDENTIFIER_RE.fullmatch(name):
        return (
            None,
            Error(
                name_node if name_node is not None else node,
                f"Expected a capture name to be a valid identifier, but got: {name!r}",
            ),
        )

    return (
        Snapshot(
            args=[Identifier(arg.arg) for arg in capture_node.args.args],
            body=capture_node.body,
            name=Identifier(name),
            capture_node=capture_node,
        ),
        None,
    )


# TODO: include severity levels for contracts in the meta model and
#  consider them in the imports
# TODO: test for unknown severity level


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _function_def_to_method(
    node: ast.FunctionDef, atok: asttokens.ASTTokens
) -> Tuple[Optional[Method], Optional[Error]]:
    """Parse the function definition into an entity method."""
    name = node.name

    if name != "__init__" and name.startswith("__") and name.endswith("__"):
        return (
            None,
            Error(
                node,
                f"Among all dunder methods, only ``__init__`` is expected, "
                f"but got: {name}",
            ),
        )

    preconditions = []  # type: List[Contract]
    postconditions = []  # type: List[Contract]
    snapshots = []  # type: List[Snapshot]

    is_implementation_specific = False

    # region Parse decorators

    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                if decorator.func.id == "require":
                    precondition, error = _parse_contract_condition(
                        node=decorator, atok=atok
                    )
                    if error is not None:
                        return None, error

                    assert precondition is not None

                    preconditions.append(precondition)

                elif decorator.func.id == "ensure":
                    postcondition, error = _parse_contract_condition(
                        node=decorator, atok=atok
                    )
                    if error is not None:
                        return None, error

                    assert postcondition is not None

                    postconditions.append(postcondition)

                elif decorator.func.id == "snapshot":
                    snapshot, error = _parse_snapshot(node=decorator, atok=atok)
                    if error is not None:
                        return None, error

                    assert snapshot is not None

                    snapshots.append(snapshot)

                else:
                    return (
                        None,
                        Error(
                            decorator,
                            f"Unexpected decorator of a method: {decorator.func.id}; "
                            f"expected at most "
                            f"``require``, ``ensure`` or ``snapshot``",
                        ),
                    )
            else:
                return (
                    None,
                    Error(
                        decorator,
                        f"Unexpected non-name decorator of a method: "
                        f"{atok.get_text(decorator.func)!r}",
                    ),
                )

        elif isinstance(decorator, ast.Name):
            if decorator.id != "implementation_specific":
                return (
                    None,
                    Error(
                        decorator,
                        f"Unexpected simple decorator of a method: {decorator.id}; "
                        f"expected at most ``implementation_specific``",
                    ),
                )
            else:
                is_implementation_specific = True
        else:
            return (
                None,
                Error(
                    decorator,
                    f"Expected decorators of a method to be "
                    f"only ``ast.Name`` and ``ast.Call``, "
                    f"but got: {atok.get_text(decorator)!r}",
                ),
            )

    # endregion

    # region Reverse contracts

    # We need to reverse the contracts since the decorators are evaluated from bottom
    # up, while we parsed them from top to bottom.
    preconditions = list(reversed(preconditions))
    snapshots = list(reversed(snapshots))
    postconditions = list(reversed(postconditions))

    # endregion

    # region Parse arguments and body

    description = None  # type: Optional[str]
    body = node.body

    if len(node.body) >= 1 and is_string_expr(expr=node.body[0]):
        assert isinstance(node.body[0], ast.Expr)

        description = _string_expr_to_text(expr=node.body[0])
        body = node.body[1:]

    arguments, error = _args_to_arguments(node=node.args, atok=atok)
    if error is not None:
        return (
            None,
            Error(
                node,
                f"Failed to parse arguments of the method: {name}",
                underlying=[error],
            ),
        )

    assert arguments is not None

    returns = None  # type: Optional[TypeAnnotation]
    if node.returns is None:
        return (
            None,
            Error(
                node,
                f"Unexpected method without a type annotation for the result: {name}",
            ),
        )

    if not (isinstance(node.returns, ast.Constant) and node.returns.value is None):
        returns, error = _type_annotation(node=node.returns, atok=atok)
        if error is not None:
            return None, error

    # endregion

    # region All contract arguments are included in the function arguments

    function_arg_set = set(arg.name for arg in arguments)

    for contract in preconditions:
        for arg in contract.args:
            if arg not in function_arg_set:
                return (
                    None,
                    Error(
                        contract.condition_node,
                        f"The argument of the precondition is not provided "
                        f"in the method: {arg}",
                    ),
                )

    has_snapshots = len(snapshots) > 0
    for contract in postconditions:
        for arg in contract.args:
            if arg == "OLD":
                if not has_snapshots and arg == "OLD":
                    return (
                        None,
                        Error(
                            contract.condition_node,
                            f"The argument OLD of the postcondition is not provided "
                            f"since there were no snapshots defined "
                            f"for the method: {name}",
                        ),
                    )

            elif arg == "result":
                continue

            elif arg not in function_arg_set:
                return (
                    None,
                    Error(
                        contract.condition_node,
                        f"The argument of the postcondition is not provided "
                        f"in the method: {arg}",
                    ),
                )
            else:
                # Everything is OK.
                pass

    for snapshot in snapshots:
        for arg in snapshot.args:
            if arg not in function_arg_set:
                return (
                    None,
                    Error(
                        snapshot.capture_node,
                        f"The argument of the snapshot is not provided "
                        f"in the method: {arg}",
                    ),
                )

    # endregion

    # region __init__ must return None
    if name == "__init__" and returns is not None:
        return (
            None,
            Error(
                node,
                f"Expected __init__ to return None, "
                f"but got: {atok.get_text(node.returns)}",
            ),
        )
    # endregion

    return (
        Method(
            name=Identifier(name),
            is_implementation_specific=is_implementation_specific,
            arguments=arguments,
            returns=returns,
            description=description,
            contracts=Contracts(
                preconditions=preconditions,
                snapshots=snapshots,
                postconditions=postconditions,
            ),
            body=body,
            node=node,
        ),
        None,
    )


@require(lambda expr: is_string_expr(expr))
def _string_expr_to_text(expr: ast.Expr) -> str:
    """Extract the dedented docstring from the given expression."""
    assert isinstance(expr.value, ast.Constant), f"{ast.dump(expr)=}"

    return textwrap.dedent(expr.value.value).strip()


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _classdef_to_symbol(
    node: ast.ClassDef, atok: asttokens.ASTTokens
) -> Tuple[Optional[Symbol], Optional[Error]]:
    """Interpret the class definition as a symbol."""
    underlying_errors = []  # type: List[Error]

    base_names = []  # type: List[str]
    for base in node.bases:
        if not isinstance(base, ast.Name):
            underlying_errors.append(
                Error(
                    node=base,
                    message=f"Expected a base as a name, "
                    f"but got: {atok.get_text(base)}",
                )
            )
        else:
            base_names.append(base.id)

    if len(underlying_errors) > 0:
        return (
            None,
            Error(
                node,
                f"Failed to parse the class definition: {node.name}",
                underlying=underlying_errors,
            ),
        )

    if "Enum" in base_names and len(base_names) > 1:
        return (
            None,
            Error(
                node=node,
                message=f"Expected an enumeration to only inherit from ``Enum``, "
                f"but it inherits from: {base_names}",
            ),
        )

    if "Enum" in base_names:
        return _enum_to_symbol(node=node, atok=atok)

    # We have to parse the class definition as entity definition from here on.

    # DBC is only used for inheritance of the contracts in the meta-model
    # so that the developers tinkering with the meta-model can play with it
    # at runtime. We can safely ignore it as we are not looking into any
    # runtime code.
    inheritances = [
        Identifier(base_name) for base_name in base_names if base_name != "DBC"
    ]

    # region Decorators

    is_abstract = False
    is_implementation_specific = False
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Name):
            return (
                None,
                Error(
                    node=decorator,
                    message=f"Expected a decorator as a name, "
                    f"but got: {atok.get_text(decorator)}",
                ),
            )

        if decorator.id == "abstract":
            is_abstract = True
        elif decorator.id == "implementation_specific":
            is_implementation_specific = True
        else:
            return (
                None,
                Error(
                    node=decorator,
                    message=f"Unexpected decorator for a class: {decorator.id!r}",
                ),
            )
    # endregion

    description = None  # type: Optional[str]

    properties = []  # type: List[Property]
    methods = []  # type: List[Method]

    cursor = 0
    while cursor < len(node.body):
        old_cursor = cursor

        expr = node.body[cursor]

        if cursor == 0 and is_string_expr(expr):
            assert isinstance(expr, ast.Expr)
            description = _string_expr_to_text(expr)
            cursor += 1
            continue

        if isinstance(expr, ast.Pass):
            cursor += 1
            continue

        if isinstance(expr, ast.AnnAssign):
            property_description = None  # type: Optional[str]

            next_expr = node.body[cursor + 1] if cursor < len(node.body) - 1 else None
            if next_expr is not None and is_string_expr(next_expr):
                assert isinstance(next_expr, ast.Expr)
                property_description = _string_expr_to_text(next_expr)
                cursor += 1

            prop, error = _ann_assign_to_property(
                node=expr, description=property_description, atok=atok
            )
            cursor += 1

            if error is not None:
                return (
                    None,
                    Error(expr, "Failed to parse a property", underlying=[error]),
                )

            assert prop is not None

            properties.append(prop)

        elif isinstance(expr, ast.FunctionDef):
            method, error = _function_def_to_method(node=expr, atok=atok)
            if error is not None:
                return (
                    None,
                    Error(
                        expr,
                        f"Failed to parse the method: {expr.name}",
                        underlying=[error],
                    ),
                )

            assert method is not None
            methods.append(method)

            cursor += 1

        else:
            return (
                None,
                Error(
                    node=expr,
                    message=f"Expected only either "
                    f"properties explicitly annotated with types or "
                    f"instance methods, but got: {atok.get_text(expr)}",
                ),
            )

        assert old_cursor < cursor, f"Loop invariant: {old_cursor=}, {cursor=}"

    if is_abstract:
        entity_cls = (
            AbstractEntity
        )  # type: Union[Type[AbstractEntity], Type[ConcreteEntity]]
    else:
        entity_cls = ConcreteEntity

    return (
        entity_cls(
            name=Identifier(node.name),
            is_implementation_specific=is_implementation_specific,
            inheritances=inheritances,
            properties=properties,
            methods=methods,
            description=description,
            node=node,
        ),
        None,
    )


# fmt: off
@ensure(
    lambda result:
    result[1] is None or len(result[1]) > 0,
    "If errors are not None, there must be at least one error"
)
@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
# fmt: on
def _verify_symbol_table(
    symbol_table: UnverifiedSymbolTable,
) -> Tuple[Optional[SymbolTable], Optional[List[Error]]]:
    """
    Check that the symbol table is consistent.

    For example, check that there are no dangling references in type annotations or
    inheritances.
    """
    errors = []  # type: List[Error]

    for symbol in symbol_table.symbols:
        if not isinstance(symbol, Entity):
            continue

        for inheritance in symbol.inheritances:
            parent_symbol = symbol_table.find(name=inheritance)

            if parent_symbol is None:
                errors.append(
                    Error(
                        symbol.node,
                        f"The inheritance for entity {symbol.name} "
                        f"is dangling: {inheritance}",
                    )
                )

            elif not isinstance(parent_symbol, Entity):
                errors.append(
                    Error(
                        symbol.node,
                        f"Expected the entity {symbol.name} to inherit "
                        f"from an abstract entity, "
                        f"but it inherits from a symbol of type "
                        f"{parent_symbol.__class__.__name__}: {parent_symbol.name}",
                    )
                )

            elif not isinstance(parent_symbol, AbstractEntity):
                errors.append(
                    Error(
                        symbol.node,
                        f"Expected the entity {symbol.name} to inherit from "
                        f"an abstract entity, but it inherits "
                        f"from a non-abstract one: {parent_symbol.name}",
                    )
                )

    if len(errors) > 0:
        return None, errors

    # endregion

    # region Check for dangling type annotations in properties and method signatures

    expected_atomic_types = {"int", "float", "str", "bool"}
    expected_subscripted_types = {
        "List",
        "Sequence",
        "Set",
        "Mapping",
        "MutableMapping",
        "Optional",
        "Final",
    }

    def verify_no_dangling_references_in_type_annotation(
        type_annotation: TypeAnnotation,
    ) -> Optional[str]:
        """
        Check that the type annotation contains no dangling references.

        :return: error message, if any
        """
        if isinstance(type_annotation, AtomicTypeAnnotation):
            if type_annotation.identifier in expected_atomic_types:
                return None

            if type_annotation.identifier in expected_subscripted_types:
                return (
                    f"The type annotation is expected with subscript(s), "
                    f"but got none: {type_annotation.identifier}"
                )

            if symbol_table.find(type_annotation.identifier) is not None:
                return None

            return (
                f"The type annotation could not be found "
                f"in the symbol table: {type_annotation.identifier}"
            )

        elif isinstance(type_annotation, SubscriptedTypeAnnotation):
            if type_annotation.identifier not in expected_subscripted_types:
                return f"Unexpected subscripted type: {type_annotation.identifier}"

            for subscript in type_annotation.subscripts:
                error = verify_no_dangling_references_in_type_annotation(
                    type_annotation=subscript
                )
                if error is not None:
                    return error

            return None

        elif isinstance(type_annotation, SelfTypeAnnotation):
            return None

        else:
            assert_never(type_annotation)
            raise AssertionError(type_annotation)

    for symbol in symbol_table.symbols:
        if not isinstance(symbol, Entity):
            continue

        for prop in symbol.properties:
            error_message = verify_no_dangling_references_in_type_annotation(
                type_annotation=prop.type_annotation
            )

            if error_message is not None:
                errors.append(Error(prop.node, error_message))

        for method in symbol.methods:
            for arg in method.arguments:
                error_message = verify_no_dangling_references_in_type_annotation(
                    type_annotation=arg.type_annotation
                )

                if error_message is not None:
                    errors.append(Error(arg.node, error_message))

    if len(errors) > 0:
        return None, errors

    # endregion

    return cast(SymbolTable, symbol_table), None


@require(lambda atok: isinstance(atok.tree, ast.Module))
@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def _atok_to_symbol_table(
    atok: asttokens.ASTTokens,
) -> Tuple[Optional[SymbolTable], Optional[Error]]:
    symbols = []  # type: List[Symbol]
    underlying_errors = []  # type: List[Error]

    for node in atok.tree.body:
        if isinstance(node, ast.ClassDef):
            symbol, symbol_error = _classdef_to_symbol(node=node, atok=atok)
            if symbol_error:
                underlying_errors.append(
                    Error(
                        node,
                        f"Failed to parse the class definition: {node.name}",
                        [symbol_error],
                    )
                )
            else:
                assert symbol is not None
                symbols.append(symbol)

    if len(underlying_errors) > 0:
        return (None, Error(atok.tree, "Failed to parse the AST", underlying_errors))

    unverified_symbol_table = UnverifiedSymbolTable(symbols=symbols)

    symbol_table, verification_errors = _verify_symbol_table(unverified_symbol_table)

    if verification_errors is not None:
        return (
            None,
            Error(
                atok.tree, "Verification of the meta-model failed", verification_errors
            ),
        )

    assert symbol_table is not None
    return symbol_table, None


@require(lambda atok: isinstance(atok.tree, ast.Module))
@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def atok_to_symbol_table(
    atok: asttokens.ASTTokens,
) -> Tuple[Optional[SymbolTable], Optional[Error]]:
    """Construct the symbol table based on the parsed AST."""
    table, error = _atok_to_symbol_table(atok=atok)
    if error is not None:
        return None, error

    return table, None
