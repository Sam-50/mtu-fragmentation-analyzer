"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.config import BASE_DIR, settings
from app.routes.api import router as api_router
from app.routes.dashboard import router as dashboard_router


db.init_db()

app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
app.include_router(api_router)
app.include_router(dashboard_router)
