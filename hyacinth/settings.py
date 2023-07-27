import logging
from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    # timezone
    tz: str

    # logging config
    log_level: int = logging.DEBUG
    log_format: str = "%(asctime)s [%(process)d] [%(levelname)s] %(name)-16s %(message)s"
    log_date_format: str = "%Y-%m-%d %H:%M:%S"

    # list of plugin paths to load on start-up
    plugins: list[str] = [
        "plugins.craigslist.plugin:CraigslistPlugin",
    ]

    # db credentials
    postgres_user: str
    postgres_password: str

    # the local geocoding implementation does not require a google API key, but requires first
    # downloading some spatial data and only supports the US
    use_local_geocoder: bool = True

    # google geocoding credentials
    google_geocoding_api_key: str

    # craigslist data files
    craigslist_areas_reference_json_path: Path = Path("craigslist_areas.json")

    # polling intervals for different sources
    craigslist_poll_interval_seconds: int = 600

    discord_token: str

    # immediately send notifications for listings this far in the past after creating a new notifier
    notifier_backdate_time_hours: int = 6

    # how often to check the database for new listings to notify each channel about
    notification_frequency_seconds: int = 15

    # for some sources, thumbnails may be mirrored to s3 before display
    # this is to account for some websites blocking discord from loading the image preview in the
    # notification embed
    # requires s3 credentials
    enable_s3_thumbnail_mirroring: bool = False
    s3_image_mirror_expiration_days = 1
    s3_url: str | None
    s3_access_key: str | None
    s3_secret_key: str | None
    s3_bucket: str | None

    # sources are scraped using browserless, a headless browser, to avoid bot detection
    browserless_url: str = "http://browserless:3000"

    # Development setings
    disable_search_polling: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    # missing arguments detected by mypy are sourced from .env file
    return Settings()  # type: ignore
