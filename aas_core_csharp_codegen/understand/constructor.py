"""Understand the constructors of the entities."""
import ast
import collections
import itertools
from typing import (
    List,
    Optional,
    MutableMapping,
    Mapping,
    Sequence,
    Union,
    Tuple,
    AbstractSet,
)

import asttokens
from icontract import ensure

from aas_core_csharp_codegen import parse
from aas_core_csharp_codegen.common import Identifier, Error


class CallSuperConstructor:
    """
    Represent a call to the constructor of a super class.

    The arguments of the original ``__init__`` are expected to be propagated as-are.
    """

    super_name: Identifier  #: Identifier of the super class

    def __init__(self, super_name: Identifier) -> None:
        """Initialize with the given values."""
        self.super_name = super_name


class AssignProperty:
    """Represent an assignment of an argument to ``__init__`` to a property."""

    name: Identifier  #: Identifier of the property

    def __init__(self, name: Identifier) -> None:
        """Initialize with the given values."""
        self.name = name


Statement = Union[CallSuperConstructor, AssignProperty]


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _call_as_call_to_super_init(
    call: ast.Call,
    entity: parse.Entity,
    symbol_table: parse.SymbolTable,
    atok: asttokens.ASTTokens,
) -> Tuple[Optional[CallSuperConstructor], Optional[Error]]:
    """Understand a call as a call to the constructor of a super-class."""
    if not isinstance(call.func, ast.Attribute):
        return (
            None,
            Error(
                call,
                f"Unexpected call in the body "
                f"of ``__init__``: {atok.get_text(call.func)}; "
                f"only calls to super ``__init__``'s are expected",
            ),
        )

    if call.func.attr != "__init__":
        return (
            None,
            Error(
                call,
                f"Unexpected call in the body "
                f"of ``__init__``: {atok.get_text(call.func)}; "
                f"only calls to super ``__init__``'s are expected",
            ),
        )

    if not isinstance(call.func.value, ast.Name):
        return (
            None,
            Error(
                call.func.value,
                f"Expected a super class as a name "
                f"for a call to super ``__init__``, "
                f"but got: {atok.get_text(call.func.value)}",
            ),
        )

    identifier = Identifier(call.func.value.id)

    if identifier not in entity.inheritances:
        return (
            None,
            Error(
                call.func.value,
                f"Expected a super class in the call "
                f"to a super ``__init__``, "
                f"but {entity.name} does not inherit "
                f"from {identifier}",
            ),
        )

    super_entity = symbol_table.must_find_entity(name=identifier)

    if "__init__" not in super_entity.method_map:
        return (
            None,
            Error(
                call.func,
                f"The super entity {super_entity.name} "
                f"does not define a ``__init__``",
            ),
        )

    # region Check the arguments of the call to super ``__init__``

    double_star_keyword = next(
        (keyword for keyword in call.keywords if keyword.arg is None), None
    )

    if double_star_keyword is not None:
        return (
            None,
            Error(
                double_star_keyword,
                f"Expected a call to a super ``__init__`` to provide only "
                f"explicit keyword arguments, "
                f"but got a double-star keyword argument",
            ),
        )

    underlying_errors = []  # type: List[Error]

    for arg_node in itertools.chain(
        call.args, (keyword.value for keyword in call.keywords)
    ):
        if not isinstance(arg_node, ast.Name):
            underlying_errors.append(
                Error(
                    arg_node,
                    f"Expected only names in the arguments to "
                    f"super ``__init__``, but got: {atok.get_text(arg_node)}",
                )
            )

    if len(underlying_errors) > 0:
        return (
            None,
            Error(
                call,
                "Failed to parse the arguments to the super ``__init__``",
                underlying_errors,
            ),
        )

    super_init = super_entity.method_map[Identifier("__init__")]
    resolved_kwargs = dict()  # type: MutableMapping[str, str]

    if len(call.args) > len(super_init.arguments):
        return (
            None,
            Error(
                call,
                f"The ``{super_entity.name}.__init__`` "
                f"expected {len(super_init.arguments)} argument(s), "
                f"but the call provides "
                f"{len(call.args)} positional argument(s)",
            ),
        )

    for arg_node, argument in zip(call.args, super_init.arguments):
        assert isinstance(arg_node, ast.Name)
        resolved_kwargs[argument.name] = arg_node.id

    assert len(underlying_errors) == 0

    for keyword in call.keywords:
        if keyword.arg not in super_init.argument_map:
            underlying_errors.append(
                Error(
                    keyword,
                    f"The ``{super_entity.name}.__init__`` does not expect "
                    f"the argument {keyword.arg}",
                )
            )
        else:
            assert isinstance(keyword.value, ast.Name)
            assert isinstance(keyword.arg, str)
            resolved_kwargs[keyword.arg] = keyword.value.id

    if len(underlying_errors) > 0:
        return (
            None,
            Error(
                call,
                "Failed to parse the arguments to the super ``__init__``",
                underlying_errors,
            ),
        )

    init = entity.method_map[Identifier("__init__")]
    for key, val in resolved_kwargs.items():
        if val not in init.argument_map:
            underlying_errors.append(
                Error(
                    call,
                    f"Expected all the arguments to "
                    f"``{super_entity.name}.__init__`` "
                    f"to be propagation of the original ``__init__`` "
                    f"arguments, but the name {key} is not an argument "
                    f"of ``{entity.name}.__init__``",
                )
            )

        elif key != val:
            underlying_errors.append(
                Error(
                    call,
                    f"Expected the arguments to super ``__init__`` "
                    f"to be passed with the same names, "
                    f"but the argument {key} is passed "
                    f"as the name {val}",
                )
            )

    missing_args = [
        argument.name
        for argument in super_init.arguments
        if argument.name not in resolved_kwargs
    ]

    if len(missing_args) > 0:
        missing_args_str = ", ".join(missing_args)
        underlying_errors.append(
            Error(
                call,
                f"The call to ``{super_entity.name}.__init__`` "
                f"is missing one or more arguments: "
                f"{missing_args_str}",
            )
        )

    if len(underlying_errors) > 0:
        return (
            None,
            Error(
                call,
                "Failed to parse the arguments to the super ``__init__``",
                underlying_errors,
            ),
        )
    # endregion

    return CallSuperConstructor(super_name=super_entity.name), None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _assign_as_property_assignment(
    assign: ast.Assign, entity: parse.Entity, atok: asttokens.ASTTokens
) -> Tuple[Optional[AssignProperty], Optional[Error]]:
    if len(assign.targets) > 1:
        return (
            None,
            Error(
                assign,
                f"Expected only a single target for property assignment, "
                f"but got {len(assign.targets)} targets",
            ),
        )

    target = assign.targets[0]

    if not (
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id == "self"
    ):
        return (
            None,
            Error(
                target,
                f"Expected a property as the target of an assignment, "
                f"but got: {atok.get_text(target)}",
            ),
        )

    if target.attr not in entity.property_map:
        return (
            None,
            Error(
                target.value,
                f"The property has not been previously "
                f"defined in {entity.name}: {target.attr}",
            ),
        )

    if not isinstance(assign.value, ast.Name):
        return (
            None,
            Error(
                assign.value,
                f"Expected a name as the value to be assigned to the property, "
                f"but got: {atok.get_text(assign.value)}",
            ),
        )

    if target.attr != assign.value.id:
        return (
            None,
            Error(
                assign.value,
                f"Expected the property {target.attr} to be assigned "
                f"exactly the argument with the same name, "
                f"but got: {atok.get_text(assign.value)}",
            ),
        )

    return AssignProperty(name=Identifier(target.attr)), None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _understand_body(
    entity: parse.Entity, symbol_table: parse.SymbolTable, atok: asttokens.ASTTokens
) -> Tuple[Optional[List[Statement]], Optional[Error]]:
    """Try to understand the body of the constructor for the given ``entity``."""
    init = None  # type: Optional[parse.Method]
    for method in entity.methods:
        if method.name == "__init__":
            init = method
            break

    if init is None:
        return [], None

    errors = []  # type: List[Error]
    result = []  # type: List[Statement]

    for stmt in init.body:
        if isinstance(stmt, ast.Pass):
            continue
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call_super_init, error = _call_as_call_to_super_init(
                call=stmt.value, entity=entity, symbol_table=symbol_table, atok=atok
            )

            if error is not None:
                errors.append(error)
            else:
                assert call_super_init is not None
                result.append(call_super_init)

        elif isinstance(stmt, ast.Assign):
            prop_assignment, error = _assign_as_property_assignment(
                assign=stmt, entity=entity, atok=atok
            )

            if error is not None:
                errors.append(error)
            else:
                assert prop_assignment is not None
                result.append(prop_assignment)
        else:
            errors.append(
                Error(
                    stmt,
                    f"Unexpected statement in the body "
                    f"of ``__init__``: {atok.get_text(stmt)}; "
                    f"only calls to super ``__init__``'s and "
                    f"property assignments expected",
                )
            )

    if len(errors) > 0:
        return (
            None,
            Error(init.node, "Failed to understand the constructor", underlying=errors),
        )

    return result, None


class ConstructorTable:
    """Map understanding of constructors for the entities."""

    def __init__(self, mapping: Mapping[parse.Entity, Sequence[Statement]]) -> None:
        self._mapping = mapping

    def has(self, entity: parse.Entity) -> bool:
        """Check whether there is an entry in the table for the given ``entity``."""
        return entity in self._mapping

    def must_find(self, entity: parse.Entity) -> Sequence[Statement]:
        """
        Find the constructor corresponding to this entity.

        :raise: :py:attr:`KeyError` if the entry does not exist.
        """
        result = self._mapping.get(entity, None)
        if result is None:
            raise KeyError(
                f"No entry found in the constructor table for the entity: {entity}"
            )

        return result

    def entries(self) -> AbstractSet[Tuple[parse.Entity, Sequence[Statement]]]:
        """Retrieve all the entries in the table."""
        return self._mapping.items()


# fmt: off
@ensure(
    lambda symbol_table, result:
    result[0] is None
    or all(
        result[0].has(symbol)
        for symbol in symbol_table.symbols
        if isinstance(symbol, parse.Entity)
    ),
    "Constructor understood for each entity"
)
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
# fmt: on
def understand_all(
    symbol_table: parse.SymbolTable, atok: asttokens.ASTTokens
) -> Tuple[Optional[ConstructorTable], Optional[Error]]:
    """Understand the constructors of all the entities in the symbol table."""
    errors = []  # type: List[Error]
    mapping = (
        collections.OrderedDict()
    )  # type: MutableMapping[parse.Entity, List[Statement]]

    for symbol in symbol_table.symbols:
        if not isinstance(symbol, parse.Entity):
            continue

        statements, error = _understand_body(
            entity=symbol, symbol_table=symbol_table, atok=atok
        )

        if error is not None:
            errors.append(error)
        else:
            assert statements is not None
            mapping[symbol] = statements

    if len(errors) > 0:
        return (
            None,
            Error(
                atok.tree, "Failed to understand the constructors", underlying=errors
            ),
        )

    return ConstructorTable(mapping=mapping), None
