"""Heuristic TCP symptom analysis."""

from __future__ import annotations

from dataclasses import asdict

from app.models import HeuristicFinding


def analyze_tcp_symptoms(
    probes: list[dict[str, object]],
    measurement: dict[str, object],
    inferred_path_mtu: int | None,
) -> list[dict[str, object]]:
    """Infer conservative TCP-level symptoms from probe behavior."""

    findings: list[dict[str, object]] = []
    success_by_payload: dict[int, list[dict[str, object]]] = {}
    for probe in probes:
        success_by_payload.setdefault(int(probe["payload_size"]), []).append(probe)

    payloads = sorted(success_by_payload)
    threshold_payload = None
    for payload in payloads:
        records = success_by_payload[payload]
        if any(record["success"] for record in records):
            threshold_payload = payload
        else:
            break

    loss_rate = float(measurement["loss_rate"])
    max_rtt = measurement.get("max_rtt_ms")
    min_rtt = measurement.get("min_rtt_ms")

    if inferred_path_mtu and threshold_payload:
        failing_above_threshold = [
            payload for payload in payloads if payload > threshold_payload and not any(p["success"] for p in success_by_payload[payload])
        ]
        if failing_above_threshold:
            findings.append(
                asdict(
                    HeuristicFinding(
                        likely_issue="size-threshold-stall",
                        confidence="high",
                        heuristic=True,
                        explanation=(
                            "Probe success drops sharply above a specific payload size. This pattern is consistent "
                            "with PMTU or fragmentation trouble rather than uniform congestion."
                        ),
                        evidence={
                            "largest_successful_payload": threshold_payload,
                            "failing_payloads": failing_above_threshold[:5],
                            "inferred_path_mtu": inferred_path_mtu,
                        },
                    )
                )
            )

    if loss_rate >= 0.4 and threshold_payload is None:
        findings.append(
            asdict(
                HeuristicFinding(
                    likely_issue="generic-loss-or-filtering",
                    confidence="medium",
                    heuristic=True,
                    explanation=(
                        "Loss is elevated across payload sizes without a clean size threshold. This is more consistent "
                        "with filtering, host unreachability, or generic congestion than a pure MTU problem."
                    ),
                    evidence={"loss_rate": loss_rate},
                )
            )
        )

    if max_rtt is not None and min_rtt is not None and (max_rtt - min_rtt) > 80:
        findings.append(
            asdict(
                HeuristicFinding(
                    likely_issue="latency-variation",
                    confidence="low",
                    heuristic=True,
                    explanation=(
                        "RTT varies substantially between probes. This can indicate queueing or path variability, "
                        "so fragmentation should not be treated as the sole explanation."
                    ),
                    evidence={"min_rtt_ms": min_rtt, "max_rtt_ms": max_rtt},
                )
            )
        )

    if not findings:
        findings.append(
            asdict(
                HeuristicFinding(
                    likely_issue="no-strong-tcp-symptom",
                    confidence="low",
                    heuristic=True,
                    explanation=(
                        "The available probe data does not show a strong TCP symptom signature. The result should be "
                        "treated as baseline measurement rather than proof of a fragmentation-related fault."
                    ),
                    evidence={"loss_rate": loss_rate},
                )
            )
        )

    return findings
