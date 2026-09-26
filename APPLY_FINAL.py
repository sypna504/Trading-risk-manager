from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent

REPLACEMENTS = {
    ROOT / "app/ml_services/app/features_builder.py": [
        ("result[column] = result[column].astype(str)", "result[column] = result[column].astype(str).astype(object)"),
    ],
    ROOT / "app/ml_services/app/training/train_model.py": [
        ("result[column] = result[column].astype(str)", "result[column] = result[column].astype(str).astype(object)"),
        ("features[column] = features[column].astype(str)", "features[column] = features[column].astype(str).astype(object)"),
    ],
}


def main() -> int:
    patched = 0
    for path, replacements in REPLACEMENTS.items():
        if not path.exists():
            print(f"skip regression patch; base file not present in overlay-only directory: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        changed = False
        for old, new in replacements:
            if new in text:
                continue
            if old not in text:
                raise SystemExit(f"expected regression target not found: {path.relative_to(ROOT)} :: {old}")
            text = text.replace(old, new, 1)
            changed = True
        if changed:
            path.write_text(text, encoding="utf-8")
            patched += 1
            print(f"patched {path.relative_to(ROOT)}")
    stale = ROOT / "app/backend/api/app/main.py.rej"
    if stale.exists():
        stale.unlink()
        print("removed stale app/backend/api/app/main.py.rej")
    print(f"final overlay ready; regression files patched={patched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
