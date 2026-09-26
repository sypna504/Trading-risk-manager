from __future__ import annotations

import json
from pathlib import Path
from fastapi import APIRouter

from ..config import settings

router=APIRouter(prefix="/models",tags=["models"])

@router.get("/registry")
def registry():
    path=Path(settings.MODEL_REGISTRY_PATH)
    if not path.exists(): return {"available":False,"candidate_history":[]}
    try:
        payload=json.loads(path.read_text(encoding="utf-8"));payload["available"]=True;return payload
    except Exception as error:
        return {"available":False,"error":str(error),"candidate_history":[]}
