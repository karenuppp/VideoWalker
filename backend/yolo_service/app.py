"""YOLO inference service for VideoWalker."""
from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel


@dataclass
class DetectionItem:
    cls: int
    label: str
    confidence: float
    xyxy: list[float]


class InferResponse(BaseModel):
    detected: bool
    confidence: float
    description: str
    details: dict[str, Any]
    boxes: list[dict[str, Any]]
    labels: list[str]


class ModelRegistry:
    """Caches YOLO model instances and resolves model file path."""

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}
        self._lock = Lock()
        self.models_root = Path(os.getenv("YOLO_MODELS_DIR", str(Path(__file__).resolve().parent / "models"))).resolve()
        self.models_root.mkdir(parents=True, exist_ok=True)

    def _resolve_model_path(self, model_name: str) -> Path:
        filename = model_name if model_name.endswith(".pt") else f"{model_name}.pt"
        return (self.models_root / filename).resolve()

    def list_models(self) -> list[str]:
        models: list[str] = []
        for item in self.models_root.glob("*.pt"):
            if item.is_file():
                models.append(item.stem)
        return sorted(set(models))

    def get(self, model_name: str):
        with self._lock:
            if model_name in self._models:
                return self._models[model_name]

            model_path = self._resolve_model_path(model_name)
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Model file not found for model_name={model_name}, path={model_path}"
                )

            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise RuntimeError(
                    "ultralytics is not installed. Install dependencies in backend/yolo_service/requirements.txt"
                ) from exc

            model = YOLO(str(model_path))
            self._models[model_name] = model
            return model


app = FastAPI(title="VideoWalker YOLO Service", version="1.0.0")
registry = ModelRegistry()
YOLO_API_KEY = os.getenv("YOLO_API_KEY", "")


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
        "models_root": str(registry.models_root),
        "loaded_models": list(registry._models.keys()),
        "available_models": registry.list_models(),
    }


@app.get("/models")
async def list_models() -> dict[str, Any]:
    return {
        "models": registry.list_models(),
    }


@app.post("/infer", response_model=InferResponse)
async def infer(
    image: UploadFile = File(...),
    scene_key: str = Form(...),
    model_name: str = Form(...),
    confidence_threshold: float = Form(0.25),
    authorization: str | None = Header(default=None),
) -> InferResponse:
    _check_api_key(authorization)

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="image must be an image/* file")

    try:
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="empty image content")

        model = registry.get(model_name)

        # Use PIL image to avoid temporary file overhead.
        from PIL import Image

        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = model.predict(source=pil_image, verbose=False)

        detections: list[DetectionItem] = []
        max_conf = 0.0

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
                    xyxy = [float(v) for v in box.xyxy[0].tolist()]
                    label = str(names.get(cls_id, cls_id))
                    detections.append(
                        DetectionItem(
                            cls=cls_id,
                            label=label,
                            confidence=conf,
                            xyxy=xyxy,
                        )
                    )

        detected = len(detections) > 0
        labels = list({item.label for item in detections})
        class_counts: dict[str, int] = {}
        for item in detections:
            class_counts[item.label] = class_counts.get(item.label, 0) + 1
        boxes_payload = [
            {
                "cls": item.cls,
                "label": item.label,
                "confidence": item.confidence,
                "xyxy": item.xyxy,
            }
            for item in detections
        ]

        description = (
            f"Detected {len(detections)} objects for scene={scene_key}" if detected else f"No target detected for scene={scene_key}"
        )

        return InferResponse(
            detected=detected,
            confidence=max_conf,
            description=description,
            details={
                "scene_key": scene_key,
                "model_name": model_name,
                "confidence_threshold": confidence_threshold,
                "count": len(detections),
                "total_count": len(detections),
                "class_counts": class_counts,
            },
            boxes=boxes_payload,
            labels=labels,
        )

    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"infer failed: {exc}") from exc
