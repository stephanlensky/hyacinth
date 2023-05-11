import ast
import re
from dataclasses import dataclass
from typing import Any, Literal

from boolean import Expression

from hyacinth.db.models import Filter
from hyacinth.enums import RuleType
from hyacinth.util.boolean_rule_algebra import apply_rules, parse_rule


@dataclass
class NumericRule:
    operator: Literal["<", "<=", ">", ">=", "="]
    operand: int | float


def test(listing: dict[str, Any], filters: list[Filter]) -> bool:
    and_result = True
    or_result = False
    has_no_or_rules = True

    for filter_ in filters:
        if filter_.field not in listing:
            continue

        result = _apply_rule_expr(filter_.rule_expr, listing[filter_.field])

        if filter_.rule_type == RuleType.AND:
            and_result = and_result and result
        elif filter_.rule_type == RuleType.OR:
            or_result = or_result or result
            has_no_or_rules = False
        else:
            raise ValueError(f"Invalid rule type: {filter_.rule_type}")

    return and_result and (or_result or has_no_or_rules)


def _apply_rule_expr(expr: str, field: Any) -> bool:
    if isinstance(field, str):
        return _apply_string_rule_expr(expr, field)
    elif isinstance(field, int) or isinstance(field, float):
        return _apply_numeric_rule_expr(expr, field)

    raise ValueError(f"Invalid field type: {type(field)}")


def _apply_numeric_rule_expr(expr: str, field: float | int) -> bool:
    rule = parse_numeric_rule_expr(expr)
    if rule.operator == "<":
        return field < rule.operand
    elif rule.operator == "<=":
        return field <= rule.operand
    elif rule.operator == ">":
        return field > rule.operand
    elif rule.operator == ">=":
        return field >= rule.operand
    elif rule.operator == "=":
        return field == rule.operand

    raise ValueError(f"Invalid operator: {rule.operator}")


def _apply_string_rule_expr(expr: str, field: str) -> bool:
    rule = parse_string_rule_expr(expr)
    return apply_rules([rule], field)


def parse_string_rule_expr(expr: str) -> Expression:
    """
    Parse a string rule expression into a boolean expression.
    """
    return parse_rule(expr)


def parse_numeric_rule_expr(expr: str) -> NumericRule:
    match = re.match(r"(?P<operator><|<=|>|>=|=)\s*(?P<operand>\d+(\.\d+)?)", expr)
    if match is None:
        raise ValueError(f"Invalid numeric rule expression: {expr}")

    operator: Literal["<", "<=", ">", ">=", "="] = match.group("operator")  # type: ignore
    operand: Any = ast.literal_eval(match.group("operand"))

    if not isinstance(operand, (float, int)):
        raise ValueError(f"Invalid operand type: {type(operand)}")

    return NumericRule(operator=operator, operand=operand)
