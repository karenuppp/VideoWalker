"""YOLO detector service (compatible replacement for previous AIService)."""

from typing import Dict, Optional

import httpx

from app.config import settings
from app.utils.exceptions import AIServiceException
from app.utils.logger import logger


class AIService:
    """Compatibility class name retained; implementation uses YOLO detector API."""

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or settings.YOLO_API_URL
        self.timeout = settings.YOLO_TIMEOUT
        self.api_key = settings.YOLO_API_KEY
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def detect_scene(
        self,
        image_path: str,
        scene_key: str,
        model_name: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        detect_api: Optional[str] = None,
    ) -> Dict:
        if not model_name:
            raise AIServiceException("model_name is required for YOLO detect_scene")
        selected_model = model_name
        threshold = confidence_threshold if confidence_threshold is not None else 0.0
        endpoint = detect_api or self.api_url

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = {
            "scene_key": scene_key,
            "model_name": selected_model,
            "confidence_threshold": str(threshold),
        }

        try:
            with open(image_path, "rb") as fp:
                files = {"image": (image_path.split("/")[-1], fp, "image/jpeg")}
                response = await self.client.post(
                    endpoint,
                    data=data,
                    files=files,
                    headers=headers,
                )

            if response.status_code != 200:
                logger.error(
                    f"YOLO API failed: endpoint={endpoint}, status={response.status_code}, body={response.text}"
                )
                raise AIServiceException(f"YOLO API failed: HTTP {response.status_code}")

            raw = response.json()
            detection = self._normalize_result(raw, scene_key, selected_model)
            logger.info(
                "YOLO detection complete: "
                f"scene={scene_key}, model={selected_model}, "
                f"detected={detection['detected']}, confidence={detection['confidence']}"
            )
            return detection

        except FileNotFoundError:
            raise AIServiceException(f"Image file not found: {image_path}")
        except httpx.TimeoutException as e:
            raise AIServiceException(f"YOLO API timeout: {e}")
        except httpx.HTTPError as e:
            raise AIServiceException(f"YOLO API HTTP error: {e}")
        except AIServiceException:
            raise
        except Exception as e:
            logger.error(f"YOLO detect error: {e}")
            raise AIServiceException(f"YOLO detect error: {e}")

    def _normalize_result(self, raw: Dict, scene_key: str, model_name: str) -> Dict:
        detected = bool(raw.get("detected", raw.get("hit", False)))
        confidence = raw.get("confidence", raw.get("score", 0.0))
        description = raw.get("description", "")
        details = raw.get("details", {})

        if not isinstance(details, dict):
            details = {"raw_details": details}

        details.setdefault("model_name", model_name)
        details.setdefault("boxes", raw.get("boxes", []))
        details.setdefault("labels", raw.get("labels", []))

        return {
            "detected": detected,
            "confidence": float(confidence or 0.0),
            "description": description,
            "details": details,
            "scene_type": scene_key,
        }

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None
