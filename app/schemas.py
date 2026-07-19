"""Pydantic schemas for API request and response bodies."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalysisRequest(BaseModel):
    """User-submitted analysis request."""

    target: str = Field(..., min_length=1, max_length=255)
    payload_start: int = Field(1200, ge=576, le=2000)
    payload_stop: int = Field(1472, ge=576, le=2000)
    payload_step: int = Field(16, ge=1, le=256)
    probe_count: int = Field(3, ge=1, le=10)
    timeout: float = Field(2.0, ge=0.2, le=10.0)

    @field_validator("payload_stop")
    @classmethod
    def ensure_range(cls, value: int, info) -> int:
        start = info.data.get("payload_start", 1200)
        if value < start:
            raise ValueError("payload_stop must be greater than or equal to payload_start")
        return value


class ProbeResultSchema(BaseModel):
    payload_size: int
    mtu_estimate: int
    success: bool
    rtt_ms: float | None
    error_type: str | None
    detail: str | None
    method: str
    sequence_no: int
    created_at: str


class MeasurementSchema(BaseModel):
    probe_count: int
    success_count: int
    loss_rate: float
    avg_rtt_ms: float | None
    min_rtt_ms: float | None
    max_rtt_ms: float | None
    throughput_kbps: float | None
    jitter_ms: float | None
    created_at: str


class FindingSchema(BaseModel):
    likely_issue: str
    confidence: Literal["low", "medium", "high"]
    heuristic: bool
    explanation: str
    evidence: dict[str, object]
    created_at: str


class RecommendationSchema(BaseModel):
    category: str
    title: str
    detail: str
    value: str | None
    created_at: str


class AnalysisResponse(BaseModel):
    run_id: int
    target: str
    target_ip: str | None
    status: str
    largest_successful_payload: int | None
    inferred_path_mtu: int | None
    recommended_mtu: int | None
    recommended_mss: int | None
    summary: dict[str, object]
    probes: list[ProbeResultSchema]
    measurement: MeasurementSchema
    findings: list[FindingSchema]
    recommendations: list[RecommendationSchema]
    notes: str | None = None
