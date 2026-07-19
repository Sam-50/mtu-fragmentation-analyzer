"""Recommendation engine for MTU-related actions."""

from __future__ import annotations

from dataclasses import asdict

from app.models import RecommendationItem
from app.services.pmtud import mtu_to_mss


def build_recommendations(
    inferred_path_mtu: int | None,
    probes: list[dict[str, object]],
    measurement: dict[str, object],
    findings: list[dict[str, object]],
) -> tuple[int | None, int | None, list[dict[str, object]]]:
    """Generate safe MTU and MSS recommendations with plain-language explanations."""

    recommendations: list[dict[str, object]] = []
    recommended_mtu = inferred_path_mtu - 8 if inferred_path_mtu else None
    recommended_mss = mtu_to_mss(recommended_mtu) if recommended_mtu else None
    loss_rate = float(measurement["loss_rate"])

    if recommended_mtu:
        recommendations.append(
            asdict(
                RecommendationItem(
                    category="mtu",
                    title="Likely safe MTU",
                    detail=(
                        "Use a slightly conservative MTU below the largest observed non-fragmenting result. "
                        "This leaves a small safety margin for path variation."
                    ),
                    value=str(recommended_mtu),
                )
            )
        )
        recommendations.append(
            asdict(
                RecommendationItem(
                    category="mss",
                    title="Suggested TCP MSS clamp",
                    detail=(
                        "Derive MSS from the recommended MTU using the standard IPv4 TCP/IP overhead. "
                        "This can help avoid oversized TCP segments across constrained paths."
                    ),
                    value=str(recommended_mss),
                )
            )
        )

    fragmentation_failures = [probe for probe in probes if probe.get("error_type") == "fragmentation-needed"]
    silent_failures = [probe for probe in probes if probe.get("error_type") == "no-reply"]

    if fragmentation_failures:
        recommendations.append(
            asdict(
                RecommendationItem(
                    category="diagnosis",
                    title="Oversized packets detected",
                    detail=(
                        "Some probes were explicitly too large for the path. This is consistent with a path MTU bottleneck "
                        "or added tunnel overhead such as VPN/IPsec encapsulation."
                    ),
                )
            )
        )

    if recommended_mtu and silent_failures and fragmentation_failures:
        recommendations.append(
            asdict(
                RecommendationItem(
                    category="diagnosis",
                    title="Possible blocked ICMP PMTUD feedback",
                    detail=(
                        "The path shows both explicit fragmentation failures and silent drops. That mix is consistent "
                        "with ICMP 'Fragmentation Needed' messages being blocked or inconsistently delivered."
                    ),
                )
            )
        )

    if recommended_mtu and recommended_mtu < 1500:
        recommendations.append(
            asdict(
                RecommendationItem(
                    category="diagnosis",
                    title="Possible tunnel or VPN overhead",
                    detail=(
                        "The inferred safe MTU is materially below Ethernet's common 1500-byte MTU. "
                        "This often happens when VPN, GRE, PPPoE, or other encapsulation consumes extra bytes."
                    ),
                    value=str(recommended_mtu),
                )
            )
        )

    if loss_rate >= 0.4 and not fragmentation_failures:
        recommendations.append(
            asdict(
                RecommendationItem(
                    category="diagnosis",
                    title="Consider generic congestion or filtering",
                    detail=(
                        "Loss is high without strong fragmentation evidence. Treat this as a possible congestion, "
                        "policy, or host-availability problem rather than a confirmed PMTU issue."
                    ),
                )
            )
        )

    if any(finding["likely_issue"] == "latency-variation" for finding in findings):
        recommendations.append(
            asdict(
                RecommendationItem(
                    category="warning",
                    title="Interpret results cautiously",
                    detail=(
                        "Latency variation suggests queueing or path fluctuation. The MTU estimate may still be useful, "
                        "but the broader performance problem could have multiple causes."
                    ),
                )
            )
        )

    if not recommendations:
        recommendations.append(
            asdict(
                RecommendationItem(
                    category="info",
                    title="No strong mitigation required",
                    detail=(
                        "The current run did not show clear fragmentation-related trouble. Keep the result as a baseline "
                        "reference and compare future runs if symptoms recur."
                    ),
                )
            )
        )

    return recommended_mtu, recommended_mss, recommendations
