from sqlalchemy.orm import Session

from hyacinth.db.models import Filter
from hyacinth.enums import RuleType


def add_filter(
    session: Session, notifier_id: int, field: str, rule_type: RuleType, rule_expr: str
) -> Filter:
    filter = Filter(
        notifier_id=notifier_id,
        field=field,
        rule_type=rule_type,
        rule_expr=rule_expr,
    )
    session.add(filter)

    return filter
