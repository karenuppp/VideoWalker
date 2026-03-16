"""Internal system APIs."""
from fastapi import APIRouter

router = APIRouter(prefix="/internal/system", tags=["internal-system"])


@router.get("/ping")
async def ping():
    return {"status": "ok"}
