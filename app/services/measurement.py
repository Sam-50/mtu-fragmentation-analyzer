"""Network measurement service."""

from __future__ import annotations

from dataclasses import asdict
from statistics import mean

from app.models import MeasurementSummary


def summarize_measurements(probes: list[dict[str, object]]) -> dict[str, object]:
    """Create RTT, loss, and throughput approximations from probe results."""

    probe_count = len(probes)
    success_rtts = [float(probe["rtt_ms"]) for probe in probes if probe["success"] and probe["rtt_ms"] is not None]
    success_count = sum(1 for probe in probes if probe["success"])
    loss_rate = round((probe_count - success_count) / probe_count, 4) if probe_count else 1.0

    throughput_samples = [
        (float(probe["payload_size"]) * 8.0) / max(float(probe["rtt_ms"]), 0.1)
        for probe in probes
        if probe["success"] and probe["rtt_ms"] is not None
    ]

    jitter_ms = None
    if success_rtts and len(success_rtts) > 1:
        deltas = [abs(success_rtts[index] - success_rtts[index - 1]) for index in range(1, len(success_rtts))]
        jitter_ms = round(mean(deltas), 3)

    summary = MeasurementSummary(
        probe_count=probe_count,
        success_count=success_count,
        loss_rate=loss_rate,
        avg_rtt_ms=round(mean(success_rtts), 3) if success_rtts else None,
        min_rtt_ms=round(min(success_rtts), 3) if success_rtts else None,
        max_rtt_ms=round(max(success_rtts), 3) if success_rtts else None,
        throughput_kbps=round(mean(throughput_samples), 3) if throughput_samples else None,
        jitter_ms=jitter_ms,
    )
    return asdict(summary)
