"""
Single-model YOLO service for the banner (拉横幅) scene.

Usage:
    uvicorn banner_service:app --host 0.0.0.0 --port 9001 --reload

Environment:
    BANNER_MODEL_PATH  Optional, path to the .pt file. Default: ./models/banner.pt
    YOLO_API_KEY       Optional, set to enable Bearer token check.
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from PIL import Image

try:
    from ultralytics import YOLO
except ImportError as exc:  # pragma: no cover - dependency error is user facing
    raise RuntimeError(
        "ultralytics is not installed. Install backend/yolo_service/requirements.txt"
    ) from exc


class InferResponse(BaseModel):
    detected: bool
    confidence: float
    description: str
    boxes: list[dict[str, Any]]
    labels: list[str]
    details: dict[str, Any]


app = FastAPI(title="VideoWalker Banner YOLO", version="1.0.0")

MODEL_PATH = Path(
    os.getenv("BANNER_MODEL_PATH", Path(__file__).resolve().parent / "models" / "banner.pt")
).resolve()
YOLO_API_KEY = os.getenv("YOLO_API_KEY", "")


def _load_model() -> YOLO:
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model file not found: {MODEL_PATH}")
    return YOLO(str(MODEL_PATH))


model = _load_model()


def _check_api_key(authorization: str | None) -> None:
    if not YOLO_API_KEY:
        return
    expected = f"Bearer {YOLO_API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="invalid authorization")


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_path": str(MODEL_PATH),
        "labels": getattr(model.model, "names", {}),
    }


@app.post("/infer", response_model=InferResponse)
async def infer(
    image: UploadFile = File(...),
    confidence_threshold: float = 0.25,
    authorization: str | None = Header(default=None),
) -> InferResponse:
    _check_api_key(authorization)

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="image must be an image/* file")

    try:
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="empty image content")

        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = model.predict(source=pil_image, verbose=False)

        boxes_payload: list[dict[str, Any]] = []
        max_conf = 0.0
        labels = []

        if results:
            result = results[0]
            names = result.names if hasattr(result, "names") else {}
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    conf = float(box.conf[0].item())
                    cls_id = int(box.cls[0].item())
                    if conf < confidence_threshold:
                        continue
                    max_conf = max(max_conf, conf)
                    label = str(names.get(cls_id, cls_id))
                    labels.append(label)
                    boxes_payload.append(
                        {
                            "cls": cls_id,
                            "label": label,
                            "confidence": conf,
                            "xyxy": [float(v) for v in box.xyxy[0].tolist()],
                        }
                    )

        detected = len(boxes_payload) > 0
        description = (
            f"Detected {len(boxes_payload)} objects for banner"
            if detected
            else "No banner detected"
        )

        return InferResponse(
            detected=detected,
            confidence=max_conf,
            description=description,
            boxes=boxes_payload,
            labels=list(set(labels)),
            details={
                "scene_key": "banner",
                "model_path": str(MODEL_PATH),
                "confidence_threshold": confidence_threshold,
                "count": len(boxes_payload),
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"infer failed: {exc}") from exc
