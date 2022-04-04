from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    google_geocoding_api_key: str

    craigslist_areas_reference_json_path: Path = Path("craigslist_areas.json")
    craigslist_areas_ini_path: Path = Path("craigslist_areas.ini")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
