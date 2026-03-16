"""User-facing alert APIs."""
from app.api.v1.alerts import router as legacy_alert_router

router = legacy_alert_router
