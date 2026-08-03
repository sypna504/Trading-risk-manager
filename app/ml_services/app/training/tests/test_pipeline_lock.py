from __future__ import annotations

import pytest

from app.training.pipeline_lock import PipelineLock


def test_lock_blocks_second_training_job(tmp_path):
    path = tmp_path / ".lock"
    with PipelineLock(path):
        with pytest.raises(RuntimeError):
            with PipelineLock(path):
                pass
    assert not path.exists()
