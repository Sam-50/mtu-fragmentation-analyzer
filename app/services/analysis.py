"""High-level orchestration for full analysis runs."""

from __future__ import annotations

from datetime import datetime, timezone
import json

from app import db
from app.schemas import AnalysisRequest
from app.services.measurement import summarize_measurements
from app.services.pmtud import (
    ProbeExecutor,
    infer_largest_successful_payload,
    payload_to_mtu,
    sweep_payloads,
    validate_target,
)
from app.services.recommendations import build_recommendations
from app.services.tcp_analysis import analyze_tcp_symptoms


def run_analysis(request: AnalysisRequest, executor: ProbeExecutor | None = None) -> dict[str, object]:
    """Execute a full analysis workflow and persist the results."""

    target, target_ip = validate_target(request.target)
    probes = sweep_payloads(
        target=target,
        payload_start=request.payload_start,
        payload_stop=request.payload_stop,
        payload_step=request.payload_step,
        probe_count=request.probe_count,
        timeout=request.timeout,
        executor=executor,
    )
    largest_successful_payload = infer_largest_successful_payload(probes)
    inferred_path_mtu = payload_to_mtu(largest_successful_payload) if largest_successful_payload else None
    measurement = summarize_measurements(probes)
    findings = analyze_tcp_symptoms(probes, measurement, inferred_path_mtu)
    recommended_mtu, recommended_mss, recommendations = build_recommendations(
        inferred_path_mtu=inferred_path_mtu,
        probes=probes,
        measurement=measurement,
        findings=findings,
    )

    summary = {
        "inferred_path_mtu": inferred_path_mtu,
        "recommended_mtu": recommended_mtu,
        "recommended_mss": recommended_mss,
        "loss_rate": measurement["loss_rate"],
        "avg_rtt_ms": measurement["avg_rtt_ms"],
        "finding_count": len(findings),
    }
    notes = (
        "Heuristic conclusions are conservative and should not be treated as proof of router misconfiguration. "
        "In WSL2, subprocess-based ping probing is preferred over raw packet methods."
    )
    run_id = db.insert_run(
        {
            "target": target,
            "target_ip": target_ip,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed" if probes else "failed",
            "largest_successful_payload": largest_successful_payload,
            "inferred_path_mtu": inferred_path_mtu,
            "recommended_mtu": recommended_mtu,
            "recommended_mss": recommended_mss,
            "summary": summary,
            "notes": notes,
        }
    )
    for probe in probes:
        db.insert_probe(run_id, probe)
    db.insert_measurement(run_id, measurement)
    for finding in findings:
        db.insert_analysis(run_id, finding)
    for recommendation in recommendations:
        db.insert_recommendation(run_id, recommendation)

    return {
        "run_id": run_id,
        "target": target,
        "target_ip": target_ip,
        "status": "completed" if probes else "failed",
        "largest_successful_payload": largest_successful_payload,
        "inferred_path_mtu": inferred_path_mtu,
        "recommended_mtu": recommended_mtu,
        "recommended_mss": recommended_mss,
        "summary": summary,
        "probes": probes,
        "measurement": measurement,
        "findings": findings,
        "recommendations": recommendations,
        "notes": notes,
    }


def get_run_details(run_id: int) -> dict[str, object] | None:
    """Fetch a persisted run and all related records."""

    run = db.fetch_run(run_id)
    if run is None:
        return None

    probes = [dict(row) for row in db.fetch_run_related("probes", run_id)]
    measurements = [dict(row) for row in db.fetch_run_related("measurements", run_id)]
    findings = [dict(row) for row in db.fetch_run_related("analyses", run_id)]
    recommendations = [dict(row) for row in db.fetch_run_related("recommendations", run_id)]

    return {
        "run_id": int(run["id"]),
        "target": run["target"],
        "target_ip": run["target_ip"],
        "status": run["status"],
        "largest_successful_payload": run["largest_successful_payload"],
        "inferred_path_mtu": run["inferred_path_mtu"],
        "recommended_mtu": run["recommended_mtu"],
        "recommended_mss": run["recommended_mss"],
        "summary": json.loads(run["summary_json"]),
        "probes": probes,
        "measurement": measurements[0] if measurements else {},
        "findings": [
            {**finding, "heuristic": bool(finding["heuristic"]), "evidence": json.loads(finding["evidence_json"])}
            for finding in findings
        ],
        "recommendations": recommendations,
        "notes": run["notes"],
    }
