from __future__ import annotations

import logging

from .config import settings


LOG_FORMAT = (
    "%(asctime)s level=%(levelname)s service=backend "
    "logger=%(name)s message=%(message)s"
)


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=LOG_FORMAT,
        force=True,
    )
