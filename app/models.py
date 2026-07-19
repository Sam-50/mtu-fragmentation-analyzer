"""Internal dataclasses used by the application."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class ProbeResult:
    payload_size: int
    mtu_estimate: int
    success: bool
    rtt_ms: float | None
    error_type: str | None
    detail: str | None
    method: str
    sequence_no: int
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(slots=True)
class MeasurementSummary:
    probe_count: int
    success_count: int
    loss_rate: float
    avg_rtt_ms: float | None
    min_rtt_ms: float | None
    max_rtt_ms: float | None
    throughput_kbps: float | None
    jitter_ms: float | None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(slots=True)
class HeuristicFinding:
    likely_issue: str
    confidence: str
    heuristic: bool
    explanation: str
    evidence: dict[str, object]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(slots=True)
class RecommendationItem:
    category: str
    title: str
    detail: str
    value: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
