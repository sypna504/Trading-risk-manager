from fastapi import APIRouter

healt_router = APIRouter()

@healt_router.post(path="/health")
async def get_health():
    return {
        "status": "ok"
    }

    







