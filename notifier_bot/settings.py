import logging
from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    log_level: int = logging.DEBUG
    log_format: str = "%(asctime)s [%(process)d] [%(levelname)s] %(name)-16s %(message)s"
    log_date_format: str = "%Y-%m-%d %H:%M:%S"

    sqlite_db_path: str = "database.db"
    postgres_user: str
    postgres_password: str

    google_geocoding_api_key: str

    craigslist_areas_reference_json_path: Path = Path("craigslist_areas.json")
    craigslist_areas_ini_path: Path = Path("craigslist_areas.ini")

    craigslist_poll_interval_seconds: int = 600

    discord_token: str

    # eventually this should be configured on a per-notifier basis
    # just set it as a constant for now
    # note for intrepid data miners: this is the MA state house, not my actual home address :)
    home_lat_long: tuple[float, float] = (42.35871993931778, -71.06382445970375)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
