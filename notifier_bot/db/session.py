from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from notifier_bot.db.models import Base
from notifier_bot.settings import get_settings

settings = get_settings()

credentials = f"{settings.postgres_user}:{settings.postgres_password}"
host = f"db:5432/{settings.postgres_user}"
engine = create_engine(f"postgresql+psycopg2://{credentials}@{host}", future=True)
Session = sessionmaker(engine)
Base.metadata.create_all(engine)
