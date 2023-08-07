from pydantic import create_model
from pytest_mock import MockerFixture

from hyacinth.discord.commands.filter import validate_filter_expr
from hyacinth.filters import parse_numeric_rule_expr

MODULE = "hyacinth.discord.commands.filter"


def test_validate_filter_expr__numeric_field_expr__passes_validation(mocker: MockerFixture) -> None:
    model_cls = create_model("SomeModel", foo=(int, ...))
    mock_plugin = mocker.Mock(listing_cls=model_cls)
    mock_parse_numeric_rule_expr = mocker.patch(f"{MODULE}.parse_numeric_rule_expr")

    validate_filter_expr([mock_plugin], "foo", ">50")
    mock_parse_numeric_rule_expr.assert_called_once_with(">50")


def test_validate_filter_expr__str_field_expr__passes_validation(mocker: MockerFixture) -> None:
    model_cls = create_model("SomeModel", foo=(str, ...))
    mock_plugin = mocker.Mock(listing_cls=model_cls)
    mock_parse_numeric_rule_expr = mocker.patch(f"{MODULE}.parse_numeric_rule_expr")

    validate_filter_expr([mock_plugin], "foo", "some filter")
    mock_parse_numeric_rule_expr.assert_not_called()
