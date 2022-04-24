from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from notifier_bot.db.models import Base
from notifier_bot.settings import get_settings

settings = get_settings()

engine = create_engine(f"sqlite+pysqlite:///{settings.sqlite_db_path}", future=True, echo=True)
Session = sessionmaker(engine)
Base.metadata.create_all(engine)
