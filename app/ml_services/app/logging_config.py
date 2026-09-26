from __future__ import annotations

import logging

from .config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=(
            "%(asctime)s level=%(levelname)s service=ml_service "
            "logger=%(name)s message=%(message)s"
        ),
        force=True,
    )
