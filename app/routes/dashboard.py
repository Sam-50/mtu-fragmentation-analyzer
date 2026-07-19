"""Dashboard routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.config import BASE_DIR
from app.services.analysis import get_run_details


templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Render the dashboard home page."""

    recent_runs = [dict(row) for row in db.fetch_recent_runs()]
    latest_run = get_run_details(int(recent_runs[0]["id"])) if recent_runs else None
    chart_context = _build_chart_context(latest_run) if latest_run else {}
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "recent_runs": recent_runs,
            "latest_run": latest_run,
            "chart_context": chart_context,
        },
    )


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_details(request: Request, run_id: int) -> HTMLResponse:
    """Render a dedicated result page."""

    run = get_run_details(run_id)
    if run is None:
        return templates.TemplateResponse(
            request,
            "results.html",
            {"request": request, "run": None, "chart_context": {}},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "results.html",
        {"request": request, "run": run, "chart_context": _build_chart_context(run)},
    )


def _build_chart_context(run: dict[str, object]) -> dict[str, object]:
    """Build chart data for Plotly rendering."""

    probes = run["probes"]
    return {
        "mtuSuccess": {
            "x": [probe["payload_size"] for probe in probes],
            "y": [1 if probe["success"] else 0 for probe in probes],
            "text": [probe["detail"] for probe in probes],
        },
        "rttByPayload": {
            "x": [probe["payload_size"] for probe in probes if probe["rtt_ms"] is not None],
            "y": [probe["rtt_ms"] for probe in probes if probe["rtt_ms"] is not None],
        },
    }
