import logging
from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    log_level: int = logging.DEBUG

    sqlite_db_path: str = "database.db"

    google_geocoding_api_key: str

    craigslist_areas_reference_json_path: Path = Path("craigslist_areas.json")
    craigslist_areas_ini_path: Path = Path("craigslist_areas.ini")

    craigslist_poll_interval_seconds: int = 600

    discord_token: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
