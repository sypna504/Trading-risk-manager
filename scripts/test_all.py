from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def python_env(*paths: Path) -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    values = [str(path) for path in paths]
    if existing:
        values.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(values)
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="Official Trading Risk Manager test entrypoint")
    parser.add_argument("--strict-environment", action="store_true")
    parser.add_argument("--with-integration", action="store_true", default=True)
    args = parser.parse_args()

    compile_targets = [path for path in (ROOT / "app", ROOT / "tests", ROOT / "scripts") if path.exists()]
    run([sys.executable, "-m", "compileall", "-q", *map(str, compile_targets)])
    run([sys.executable, "scripts/check_dependency_contract.py"])
    run([sys.executable, "scripts/check_settings_contract.py"])
    run([sys.executable, "scripts/check_patch_consistency.py"])
    proto_cmd = [sys.executable, "scripts/check_proto_contract.py"]
    if args.strict_environment:
        proto_cmd.append("--strict-generated")
    run(proto_cmd)

    regression = ROOT / "tests/regression"
    if regression.exists():
        run(
            [sys.executable, "-m", "pytest", "-q", str(regression)],
            env=python_env(ROOT),
        )

    ml_tests = ROOT / "app/ml_services/app/training/tests"
    if ml_tests.exists():
        run(
            [sys.executable, "-m", "pytest", "-q", str(ml_tests)],
            env=python_env(ROOT / "app/ml_services"),
        )

    # Existing repository-level smoke/audit tests are preserved by the overlay.
    # Avoid rerunning the new regression/integration directories here.
    top_tests = ROOT / "tests"
    if top_tests.exists():
        extra = [path for path in top_tests.iterdir() if path.name not in {"regression", "integration", "__pycache__"}]
        if extra:
            run(
                [sys.executable, "-m", "pytest", "-q", *map(str, extra)],
                env=python_env(ROOT),
            )

    if args.with_integration and (ROOT / "tests/integration").exists():
        run(
            [sys.executable, "-m", "pytest", "-q", str(ROOT / "tests/integration")],
            env=python_env(ROOT),
        )
    print("official test suite completed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
