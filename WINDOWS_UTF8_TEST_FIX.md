# Windows UTF-8 regression fix

Fixes `UnicodeDecodeError` on Windows when regression tests read UTF-8 repository files with the locale-default `cp1251` codec.

Changed file:

- `tests/regression/test_contracts.py`

All repository text reads in that regression module now use `encoding="utf-8"` explicitly.

Validation:

- `pytest -q tests/regression`: 15 passed / 0 failed
- `python scripts/test_all.py`: PASS
- ML/training: 117 passed / 0 failed
- integration: 1 skipped / 0 failed

Apply by replacing `tests/regression/test_contracts.py`, then run:

```powershell
python .\scripts\test_all.py
```
