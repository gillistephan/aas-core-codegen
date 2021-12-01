"""Infer the constraints on the length of a property value."""
from typing import Sequence, MutableMapping, Optional, Tuple, List, Union

from aas_core_codegen.common import assert_never, Error, Identifier
from icontract import require, ensure

from aas_core_codegen import intermediate
from aas_core_codegen.parse import (
    tree as parse_tree
)
from aas_core_codegen.infer_for_schema import (
    _common as infer_for_schema_common
)


class _Constraint:
    """Represent a constraint on the ``len`` of a property."""

    def __init__(self, node: parse_tree.Node) -> None:
        self.node = node


class _MinLength(_Constraint):
    """Represent the constraint that the ``len`` is ≥ ``value``."""

    def __init__(self, node: parse_tree.Node, value: int) -> None:
        """Initialize with the given values."""
        _Constraint.__init__(self, node=node)
        self.value = value


class _MaxLength(_Constraint):
    """Represent the constraint that the ``len`` is ≤ ``value``."""

    def __init__(self, node: parse_tree.Node, value: int) -> None:
        """Initialize with the given values."""
        _Constraint.__init__(self, node=node)
        self.value = value


class _ExactLength(_Constraint):
    """Represent the constraint that the ``len`` is == ``value``."""

    def __init__(self, node: parse_tree.Node, value: int) -> None:
        """Initialize with the given values."""
        _Constraint.__init__(self, node=node)
        self.value = value


# TODO: simplify shacl.py once the constraints are in place!


def _match_len_on_property(
        node: parse_tree.Node
) -> Optional[Identifier]:
    """
    Match expressions like ``len(self.something)``.

    Return the name of the property, or None, if not matched.
    """
    mtch = (
        infer_for_schema_common.match_single_arg_function_on_property(node))

    if mtch is None:
        return None

    if mtch.function == 'len':
        return mtch.prop_name

    return None


def _match_int_constant(
        node: parse_tree.Node
) -> Optional[int]:
    """Match an integer constant."""
    if (
            isinstance(node, parse_tree.Constant)
            and isinstance(node.value, int)
    ):
        return node.value

    return None


class _LenConstraintOnProperty:
    """Represent a match on an expression like ``len(self.something)``."""

    def __init__(self, prop_name: Identifier, constraint: _Constraint) -> None:
        """Initialize with the given values."""
        self.prop_name = prop_name
        self.constraint = constraint


def _match_len_constraint_on_property(
        node: parse_tree.Node
) -> Optional[_LenConstraintOnProperty]:
    """
    Match the constraint on ``len`` of a property.

    Mind that we match the constraint even for optional properties for which
    the invariant is conditioned on the property being specified (``is not None``).
    
    Return the property name and the constraint, or None if not matched.
    """
    if not isinstance(node, parse_tree.Comparison):
        return None

    constraint = None  # type: Optional[_Constraint]

    # region Match a comparison like ``len(self.something) < X``

    prop_name = _match_len_on_property(node.left)
    constant = _match_int_constant(node.right)

    if prop_name is not None and constant is not None:
        if node.op == parse_tree.Comparator.LT:
            # len(self.something) < X
            constraint = _MaxLength(node=node, value=constant - 1)
        elif node.op == parse_tree.Comparator.LE:
            # len(self.something) <= X
            constraint = _MaxLength(node=node, value=constant)
        elif node.op == parse_tree.Comparator.EQ:
            # len(self.something) == X
            constraint = _ExactLength(node=node, value=constant)
        elif node.op == parse_tree.Comparator.GT:
            # len(self.something) > X
            constraint = _MinLength(node=node, value=constant + 1)
        elif node.op == parse_tree.Comparator.GE:
            # len(self.something) >= X
            constraint = _MinLength(node=node, value=constant)
        elif node.op == parse_tree.Comparator.NE:
            # We intentionally ignore the invariants of the form len(n) != X
            # as there is no meaningful way to represent it simply in a schema.
            pass
        else:
            assert_never(node.op)

        return _LenConstraintOnProperty(prop_name=prop_name, constraint=constraint)

    # endregion

    # region Match a comparison like ``X < self.something``

    constant = _match_int_constant(node.left)
    prop_name = _match_len_on_property(node.right)

    if constant is not None and prop_name is not None:
        if node.op == parse_tree.Comparator.LT:
            # X < len(self.something)
            constraint = _MinLength(node=node, value=constant + 1)
        elif node.op == parse_tree.Comparator.LE:
            # X <= len(self.something)
            constraint = _MinLength(node=node, value=constant)
        elif node.op == parse_tree.Comparator.EQ:
            # X == len(self.something)
            constraint = _ExactLength(node=node, value=constant)
        elif node.op == parse_tree.Comparator.GT:
            # X > len(self.something)
            constraint = _MaxLength(node=node, value=constant - 1)
        elif node.op == parse_tree.Comparator.GE:
            # X >= len(self.something)
            constraint = _MaxLength(node=node, value=constant)
        elif node.op == parse_tree.Comparator.NE:
            # We intentionally ignore the invariants of the form len(n) != X
            # as there is no meaningful way to represent it simply in a schema.
            pass
        else:
            assert_never(node.op)

        return _LenConstraintOnProperty(prop_name=prop_name, constraint=constraint)

    # endregion

    return None


class LenConstraint:
    """
    Represent the constraint on the ``len`` of a property.

    Both bounds are inclusive: ``min_value ≤ len ≤ max_value``.
    """

    # fmt: off
    @require(
        lambda min_value, max_value:
        not (min_value is not None and max_value is not None)
        or 0 < min_value <= max_value
    )
    # fmt: on
    def __init__(self, min_value: Optional[int], max_value: Optional[int]) -> None:
        """Initialize with the given values."""
        self.min_value = min_value
        self.max_value = max_value


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def infer_len_constraints(
        symbol: Union[intermediate.Interface, intermediate.Class]
) -> Tuple[
    Optional[MutableMapping[intermediate.Property, LenConstraint]],
    Optional[List[Error]]
]:
    """
    Infer the constraints on ``len`` for every property of the class ``cls``.

    Even if a property is optional, the constraint will still be inferred. Please be
    careful that this does not scramble your cardinality constraints (which start from
    zero for optional properties).

    The constraints are not exhaustive. We only infer constraints based on invariants
    which involve constants. It might be that the actual invariants are tighter.
    """
    constraint_map = dict()  # MutableMapping[intermediate.Property, List[_Constraint]]

    # region Infer the constraints in the loose form from all the invariants

    # NOTE (mristin, 2021-11-30):
    # We iterate only once through the invariants instead of inferring the constraints
    # for each property individually to be able to keep linear time complexity.

    for invariant in symbol.parsed.invariants:
        len_constraint_on_prop = None  # type: Optional[_LenConstraintOnProperty]

        # Match ``self.something is None or len(self.something) < X``
        conditional_on_prop = (
            infer_for_schema_common.match_conditional_on_prop(invariant.body))

        if conditional_on_prop is not None:
            len_constraint_on_prop = (
                _match_len_constraint_on_property(conditional_on_prop.consequent))

        else:
            # Match ``len(self.something) < X``
            len_constraint_on_prop = (
                _match_len_constraint_on_property(invariant.body)
            )

        if len_constraint_on_prop is not None:
            constraints = constraint_map.get(len_constraint_on_prop.prop_name, None)
            if constraints is None:
                constraints = []
                constraint_map[len_constraint_on_prop.prop_name] = constraints

            constraints.append(len_constraint_on_prop.constraint)

    # endregion

    # region Compress the loose constraints

    result = dict()  # type: MutableMapping[intermediate.Property, LenConstraint]
    errors = []  # type: List[Error]

    for prop_name, constraints in constraint_map.items():
        min_len = None  # type: Optional[int]
        max_len = None  # type: Optional[int]
        exact_len = None  # type: Optional[int]

        for constraint in constraints:
            if isinstance(constraint, _MinLength):
                if min_len is None:
                    min_len = constraint.value
                else:
                    min_len = max(constraint.value, min_len)

            elif isinstance(constraint, _MaxLength):
                if max_len is None:
                    max_len = constraint.value
                else:
                    max_len = min(constraint.value, max_len)

            elif isinstance(constraint, _ExactLength):
                if exact_len is not None:
                    errors.append(Error(
                        symbol.parsed.node,
                        f"The property {prop_name} has conflicting invariants "
                        f"on the length: "
                        f"the exact length, {exact_len}, contradicts "
                        f"another exactly expected length {constraint.value}."))
                exact_len = constraint.value

            else:
                assert_never(constraint)

        if exact_len is not None:
            if min_len is not None and min_len > exact_len:
                errors.append(Error(
                    symbol.parsed.node,
                    f"The property {prop_name} has conflicting invariants "
                    f"on the length: the minimum length, {min_len}, "
                    f"contradicts the exactly expected length {exact_len}."))

            if min_len is not None and exact_len > max_len:
                errors.append(Error(
                    symbol.parsed.node,
                    f"The property {prop_name} has conflicting invariants "
                    f"on the length: the maximum length, {max_len}, "
                    f"contradicts the exactly expected length {exact_len}."))

        if min_len is not None and max_len is not None and min_len > max_len:
            errors.append(Error(
                symbol.parsed.node,
                f"The property {prop_name} has conflicting invariants "
                f"on the length: the minimum length, {min_len}, "
                f"contradicts the maximum length {max_len}."))

        if len(errors) > 0:
            continue

        if exact_len is not None:
            min_len = exact_len
            max_len = exact_len

        prop = symbol.properties_by_name.get(prop_name, None)
        assert prop is not None, f"Expected the property {prop_name} in the class {symbol}"

        result[prop] = LenConstraint(min_value=min_len, max_value=max_len)

    # endregion

    if len(errors) > 0:
        return None, errors

    return result, None
