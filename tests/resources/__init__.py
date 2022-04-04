from pathlib import Path


def get_resource_path(filename: str) -> Path:
    return Path(__file__).parent / filename
