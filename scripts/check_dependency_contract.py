from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "backend": ROOT / "app/backend/api/requirements.txt",
    "ml": ROOT / "app/ml_services/requirements.txt",
}
CONTRACT = {
    "grpcio": "1.81.1",
    "grpcio-tools": "1.81.1",
    "grpcio-health-checking": "1.81.1",
    "protobuf": "6.33.5",
}


def pinned_requirements(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-r"):
            continue
        if "==" in line:
            name, version = line.split("==", 1)
            result[name.strip().lower()] = version.strip()
    return result


def main() -> int:
    errors: list[str] = []
    for label, path in FILES.items():
        pins = pinned_requirements(path)
        for package, version in CONTRACT.items():
            actual = pins.get(package)
            if actual != version:
                errors.append(
                    f"{label}: {package} must be =={version}, found {actual!r}"
                )
    test_requirements = (ROOT / "requirements-test.txt").read_text(encoding="utf-8")
    for required in (
        "-r app/backend/api/requirements.txt",
        "-r app/ml_services/requirements.txt",
    ):
        if required not in test_requirements:
            errors.append(f"requirements-test.txt is missing {required!r}")
    if errors:
        raise SystemExit("dependency contract failed:\n- " + "\n- ".join(errors))
    print("dependency contract: OK")
    for package, version in CONTRACT.items():
        print(f"  {package}=={version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
