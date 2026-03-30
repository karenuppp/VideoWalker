"""
Single-model YOLO service for people counting.

Usage:
    uvicorn people_count_service:app --host 0.0.0.0 --port 9002 --reload

Environment:
    PEOPLE_MODEL_PATH     Optional, path to the .pt file. Default: ./models/yolo26s.pt
    PEOPLE_TARGET_LABELS  Optional, comma-separated labels to count. Default: person
    YOLO_API_KEY          Optional, set to enable Bearer token check.
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


app = FastAPI(title="VideoWalker People Count YOLO", version="1.0.0")

MODEL_PATH = Path(
    os.getenv("PEOPLE_MODEL_PATH", Path(__file__).resolve().parent / "models" / "yolo26s.pt")
).resolve()
YOLO_API_KEY = os.getenv("YOLO_API_KEY", "")
TARGET_LABELS = {
    label.strip().lower()
    for label in os.getenv("PEOPLE_TARGET_LABELS", "person").split(",")
    if label.strip()
}


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
@app.get("/people/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_path": str(MODEL_PATH),
        "labels": getattr(model.model, "names", {}),
        "target_labels": sorted(TARGET_LABELS),
    }


@app.get("/models")
async def list_models() -> dict[str, Any]:
    return {
        "models": [MODEL_PATH.stem],
    }


@app.post("/infer", response_model=InferResponse)
@app.post("/people/infer", response_model=InferResponse)
async def infer(
    image: UploadFile = File(...),
    scene_key: str = Form("people_count"),
    model_name: str = Form("yolo26s"),
    confidence_threshold: float = 0.1,
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
        # Map target labels to class IDs dynamically
        target_cls_ids = [
            cls_id for cls_id, label in model.names.items()
            if str(label).lower() in TARGET_LABELS
        ]
        if not target_cls_ids:
            target_cls_ids = [0]  # fallback to person class
        results = model.predict(source=pil_image, conf=confidence_threshold, classes=target_cls_ids, verbose=False)

        boxes_payload: list[dict[str, Any]] = []
        labels: list[str] = []
        max_conf = 0.0
        class_counts: dict[str, int] = {}

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
                    class_counts[label] = class_counts.get(label, 0) + 1
                    boxes_payload.append(
                        {
                            "cls": cls_id,
                            "label": label,
                            "confidence": conf,
                            "xyxy": [float(v) for v in box.xyxy[0].tolist()],
                        }
                    )

        total_count = sum(class_counts.values())
        target_count = sum(
            count for label, count in class_counts.items() if str(label).lower() in TARGET_LABELS
        )

        detected = target_count > 0
        description = (
            f"Detected {target_count} target(s) for people_count"
            if detected
            else "No target detected for people_count"
        )

        return InferResponse(
            detected=detected,
            confidence=max_conf if detected else 0.0,
            description=description,
            boxes=boxes_payload,
            labels=list(set(labels)),
            details={
                "scene_key": scene_key,
                "model_name": model_name,
                "model_path": str(MODEL_PATH),
                "confidence_threshold": confidence_threshold,
                "count": target_count,
                "total_count": total_count,
                "class_counts": class_counts,
                "target_labels": sorted(TARGET_LABELS),
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"infer failed: {exc}") from exc


@app.get("/people/models")
async def list_people_models() -> dict[str, Any]:
    return await list_models()
