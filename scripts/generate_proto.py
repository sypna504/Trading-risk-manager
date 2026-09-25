from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTO_ROOT = ROOT / "app/proto"
PROTO_FILE = PROTO_ROOT / "ml/v1/ml.proto"
DEFAULT_OUT = ROOT


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    package = output / "ml/v1"
    if (output / "ml").exists():
        shutil.rmtree(output / "ml")
    package.mkdir(parents=True, exist_ok=True)
    (output / "ml/__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{PROTO_ROOT}",
            f"--python_out={output}",
            f"--grpc_python_out={output}",
            str(PROTO_FILE),
        ],
        check=True,
    )
    for path in (package / "ml_pb2.py", package / "ml_pb2_grpc.py"):
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f"protobuf generation failed: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    generate(args.output.resolve())
    print(f"generated protobuf from {PROTO_FILE} into {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
