"""API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from app.schemas import AnalysisRequest, AnalysisResponse
from app.services.analysis import get_run_details, run_analysis
from app.services.reporting import build_human_summary, build_run_report, export_run_csv


router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Simple health route."""

    return {"status": "ok"}


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_target(request: AnalysisRequest) -> dict[str, object]:
    """Run an end-to-end PMTU analysis."""

    try:
        return run_analysis(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs/{run_id}", response_model=AnalysisResponse)
def get_run(run_id: int) -> dict[str, object]:
    """Fetch a stored run."""

    run = get_run_details(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/{run_id}/export/json")
def export_json(run_id: int) -> JSONResponse:
    """Export a JSON report."""

    run = get_run_details(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return JSONResponse(build_run_report(run))


@router.get("/runs/{run_id}/export/csv")
def export_csv(run_id: int) -> FileResponse:
    """Export probe records as CSV."""

    run = get_run_details(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    output_path = export_run_csv(run, run_id)
    return FileResponse(output_path, media_type="text/csv", filename=output_path.name)


@router.get("/runs/{run_id}/summary")
def export_summary(run_id: int) -> PlainTextResponse:
    """Return a human-readable summary."""

    run = get_run_details(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return PlainTextResponse(build_human_summary(run))
