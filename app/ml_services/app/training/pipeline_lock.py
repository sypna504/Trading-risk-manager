from __future__ import annotations

import os
from pathlib import Path


class PipelineLock:
    def __init__(self, path: Path):
        self.path = path
        self.file_descriptor: int | None = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.file_descriptor = os.open(
                self.path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError as error:
            raise RuntimeError(
                f"another retrain pipeline is running: {self.path}"
            ) from error
        os.write(self.file_descriptor, str(os.getpid()).encode("utf-8"))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.file_descriptor is not None:
            os.close(self.file_descriptor)
        self.path.unlink(missing_ok=True)
