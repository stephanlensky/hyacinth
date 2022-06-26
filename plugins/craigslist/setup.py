import re
from typing import Any

from hyacinth.discord.thread_interaction import Question
from plugins.craigslist.util import get_areas


def available_areas() -> str:
    return "\n".join([f"{i + 1}. {area}" for i, area in enumerate(get_areas().keys())])


def validate_areas(v: str, values: dict[str, Any]) -> str:
    areas = get_areas()
    try:
        selection = int(v) - 1
        selected_area = list(areas)[selection]
    except ValueError:
        if v in areas:
            selected_area = v
        else:
            raise

    area = areas[selected_area]
    values.update(area.dict())

    return selected_area


def validate_category(v: str, _values: dict[str, Any]) -> str:
    if not re.match(r"^[a-zA-Z0-9]+$", v):
        raise ValueError("Category must be alphanumeric")
    return v


questions = [
    Question(
        key="area",
        prompt=(
            "Which area of Craigslist would you like to search? Available"
            f" areas:\n```{available_areas()}```"
        ),
        validator=validate_areas,
        include_answer=False,
    ),
    Question(
        key="category",
        prompt=(
            "Which category of Craigslist would you like to search? This is the string"
            " in the Craigslist URL after `/search`. For example, `mca` for motorcycles"
            ' or `sss` for general "for sale".'
        ),
        validator=validate_category,
    ),
    Question(
        key="max_distance_miles",
        prompt=(
            "What is the maximum distance away (in miles) that you would like to show results for?"
        ),
        validator=lambda v, _values: int(v),
    ),
]
