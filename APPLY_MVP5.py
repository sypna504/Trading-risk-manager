from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPLACEMENTS = {
    ROOT / "app/ml_services/app/features_builder.py": [
        (
            "result[column] = result[column].astype(str)",
            "result[column] = result[column].astype(str).astype(object)",
        )
    ],
    ROOT / "app/ml_services/app/training/train_model.py": [
        (
            "result[column] = result[column].astype(str)",
            "result[column] = result[column].astype(str).astype(object)",
        ),
        (
            "features[column] = features[column].astype(str)",
            "features[column] = features[column].astype(str).astype(object)",
        ),
    ],
}


def main() -> int:
    for path, replacements in REPLACEMENTS.items():
        if not path.exists():
            raise SystemExit(f"missing base repository file: {path.relative_to(ROOT)}")
        text = path.read_text(encoding="utf-8")
        changed = False
        for old, new in replacements:
            if new in text:
                continue
            if old not in text:
                raise SystemExit(
                    f"expected regression target not found in {path.relative_to(ROOT)}: {old}"
                )
            text = text.replace(old, new, 1)
            changed = True
        if changed:
            path.write_text(text, encoding="utf-8")
            print(f"patched {path.relative_to(ROOT)}")
        else:
            print(f"already patched {path.relative_to(ROOT)}")
    print("MVP-5 regression fixes applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
