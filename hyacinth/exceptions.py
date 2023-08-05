class MissingPluginError(Exception):
    """A required plugin is missing"""


class MetricsWriteError(Exception):
    """An error occurred while writing metrics"""


class ParseError(Exception):
    """An error occurred while parsing a page"""

    page_content: str

    def __init__(self, message: str, page_content: str) -> None:
        super().__init__(message)
        self.page_content = page_content
