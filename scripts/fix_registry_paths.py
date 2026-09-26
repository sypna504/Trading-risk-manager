from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any


def normalize_path(value: str) -> str:
    normalized = str(value).strip().replace("\\", "/")
    if not normalized:
        raise ValueError("registry path is empty")

    path = PurePosixPath(normalized)
    parts = tuple(part for part in path.parts if part not in ("", "."))

    if path.is_absolute() or not parts:
        raise ValueError(f"registry path must be relative: {value}")
    if ".." in parts:
        raise ValueError(f"registry path traversal is not allowed: {value}")
    if ":" in parts[0]:
        raise ValueError(f"registry path must not contain a drive: {value}")

    return PurePosixPath(*parts).as_posix()


def repair(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    result = dict(payload)
    changed = False

    for key in ("active_model_path", "active_config_path"):
        value = result.get(key)
        if value:
            normalized = normalize_path(value)
            if normalized != value:
                result[key] = normalized
                changed = True

    history = []
    for item in result.get("candidate_history", []):
        updated = dict(item)
        value = updated.get("path")
        if value:
            normalized = normalize_path(value)
            if normalized != value:
                updated["path"] = normalized
                changed = True
        history.append(updated)

    result["candidate_history"] = history
    return result, changed


def atomic_write_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        default="app/ml_services/app/models/registry.json",
    )
    args = parser.parse_args()

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"registry not found: {registry_path}")
        return 1

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    repaired, changed = repair(payload)

    backup_path = registry_path.with_suffix(".json.bak")
    backup_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if changed:
        atomic_write_json(repaired, registry_path)
        print(f"registry paths fixed: {registry_path}")
    else:
        print("registry paths are already valid")

    print(f"backup: {backup_path}")
    print(f"active model: {repaired.get('active_model_path')}")
    print(f"active config: {repaired.get('active_config_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
