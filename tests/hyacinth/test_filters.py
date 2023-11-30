from hyacinth.filters import _apply_string_rule_expr, parse_string_rule_expr


def test__apply_string_rule__some_rule_expression__applies_rule_correctly() -> None:
    assert _apply_string_rule_expr("foo", "some field that contains Foo")
