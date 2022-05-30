"""
In previous versions, the only implemented filter was the StringFieldFilter and there was no
filter_type field to discriminate between different types of filters.

This migration adds filter_type=string to all filters missing the discriminator.
"""

import json

from notifier_bot.db.models import DbDiscordNotifier
from notifier_bot.db.session import Session


def main() -> None:
    updated_count = 0
    with Session() as session:
        db_notifiers: list[DbDiscordNotifier] = session.query(DbDiscordNotifier).all()
        for db_notifier in db_notifiers:
            notifier_json = json.loads(db_notifier.config_json)  # type: ignore
            updated = False
            for filter_ in notifier_json["filters"].values():
                if "filter_type" not in filter_:
                    filter_["filter_type"] = "string"
                    updated = True
                    updated_count += 1

            if updated:
                db_notifier.config_json = json.dumps(notifier_json)

        session.commit()

    print(f"Updated {updated_count} filters")


if __name__ == "__main__":
    main()
