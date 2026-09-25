from __future__ import annotations

from pathlib import Path

import pytest


def _project_root() -> Path:
    return Path(__file__).resolve().parents[5]


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/backend/api/dockerfile",
        "app/ml_services/dockerfile",
    ],
)
def test_dockerfile_makes_project_root_importable_before_protobuf_check(
    relative_path: str,
):
    dockerfile = _project_root() / relative_path
    if not dockerfile.exists():
        pytest.skip("full repository tree is not available in this test environment")

    text = dockerfile.read_text(encoding="utf-8")
    pythonpath_index = text.index("ENV PYTHONPATH=/app")
    protoc_index = text.index("python -m grpc_tools.protoc")
    markers_index = text.index("touch ./ml/__init__.py ./ml/v1/__init__.py")

    assert pythonpath_index < protoc_index
    assert markers_index < protoc_index
    assert "test -s ./ml/v1/ml_pb2.py" in text
    assert "test -s ./ml/v1/ml_pb2_grpc.py" in text
