"""Admin APIs for model registry."""
from typing import Optional
from urllib.parse import urlparse, urlunparse

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.config import settings

router = APIRouter(prefix="/admin/models", tags=["admin-models"])


def _normalize_models_url(base: str) -> str:
    if not base:
        return ""
    if base.endswith("/infer"):
        base = base[: -len("/infer")]
    return base.rstrip("/") + "/models"


@router.get("")
async def list_models(detect_api: Optional[str] = Query(None)):
    endpoint = detect_api or settings.YOLO_API_URL
    models_url = _normalize_models_url(endpoint)
    if not models_url:
        raise HTTPException(status_code=400, detail="YOLO_API_URL not configured")

    try:
        async with httpx.AsyncClient(timeout=settings.YOLO_TIMEOUT) as client:
            response = await client.get(models_url)
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"model service error: HTTP {response.status_code}")
        payload = response.json()
        models = payload.get("models", [])
        if not isinstance(models, list):
            models = []
        return {"models": models, "source": models_url}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="model service timeout")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"model service error: {exc}")
