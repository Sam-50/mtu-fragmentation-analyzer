"""Path MTU Discovery service with WSL-friendly fallbacks."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import ipaddress
import re
import shutil
import socket
import subprocess
from typing import Protocol

from app.config import settings
from app.models import ProbeResult


PING_RTT_RE = re.compile(r"time=([0-9.]+)\s*ms")


class ProbeExecutor(Protocol):
    """Abstraction for probe execution to support tests."""

    def run_probe(self, target: str, payload_size: int, timeout: float, sequence_no: int) -> ProbeResult:
        """Run a single probe and return the result."""


def validate_target(target: str) -> tuple[str, str | None]:
    """Validate a host or IP address and return its normalized form and resolved IP."""

    normalized = target.strip()
    if not normalized:
        raise ValueError("Target cannot be empty")

    try:
        ipaddress.ip_address(normalized)
        return normalized, normalized
    except ValueError:
        pass

    try:
        resolved = socket.gethostbyname(normalized)
    except socket.gaierror as exc:
        raise ValueError(f"Unable to resolve target '{normalized}'") from exc

    return normalized, resolved


def payload_to_mtu(payload_size: int, ipv6: bool = False) -> int:
    """Convert ICMP ping payload size into an approximate L3 MTU."""

    icmp_header = 8
    ip_header = 40 if ipv6 else 20
    return payload_size + icmp_header + ip_header


def mtu_to_mss(mtu: int, ipv6: bool = False) -> int:
    """Convert MTU to a likely TCP MSS clamp value."""

    overhead = settings.tcp_ipv6_header_bytes if ipv6 else settings.tcp_ipv4_header_bytes
    return max(mtu - overhead, 536 if not ipv6 else 1220)


class LinuxPingExecutor:
    """Use Linux ping subprocesses that work inside WSL2 more reliably than raw sockets."""

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or settings.ping_binary

    def run_probe(self, target: str, payload_size: int, timeout: float, sequence_no: int) -> ProbeResult:
        mtu_estimate = payload_to_mtu(payload_size)

        binary = shutil.which(self.binary) or self.binary
        command = [
            binary,
            "-c",
            "1",
            "-W",
            str(max(1, int(timeout))),
            "-M",
            "do",
            "-s",
            str(payload_size),
            target,
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout + 1.0,
                check=False,
            )
        except FileNotFoundError:
            return ProbeResult(
                payload_size=payload_size,
                mtu_estimate=mtu_estimate,
                success=False,
                rtt_ms=None,
                error_type="environment",
                detail="Linux ping utility not found. Use WSL2 Ubuntu and install iputils-ping.",
                method="ping-subprocess",
                sequence_no=sequence_no,
            )
        except subprocess.TimeoutExpired:
            return ProbeResult(
                payload_size=payload_size,
                mtu_estimate=mtu_estimate,
                success=False,
                rtt_ms=None,
                error_type="timeout",
                detail="Probe timed out before a reply or ICMP error was observed.",
                method="ping-subprocess",
                sequence_no=sequence_no,
            )

        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        lower_output = combined_output.lower()
        rtt_match = PING_RTT_RE.search(combined_output)
        rtt_ms = float(rtt_match.group(1)) if rtt_match else None

        if completed.returncode == 0 and "1 received" in lower_output:
            return ProbeResult(
                payload_size=payload_size,
                mtu_estimate=mtu_estimate,
                success=True,
                rtt_ms=rtt_ms,
                error_type=None,
                detail="Probe succeeded without fragmentation.",
                method="ping-subprocess",
                sequence_no=sequence_no,
            )

        if "message too long" in lower_output or "frag needed" in lower_output:
            detail = "Probe exceeded path MTU or local interface MTU; fragmentation would be required."
            error_type = "fragmentation-needed"
        elif "100% packet loss" in lower_output or "0 received" in lower_output:
            detail = "No reply received. This may indicate filtering, congestion, host blocking, or ICMP black-holing."
            error_type = "no-reply"
        else:
            detail = combined_output or "Probe failed without a clear ICMP diagnostic."
            error_type = "unknown"

        return ProbeResult(
            payload_size=payload_size,
            mtu_estimate=mtu_estimate,
            success=False,
            rtt_ms=rtt_ms,
            error_type=error_type,
            detail=detail,
            method="ping-subprocess",
            sequence_no=sequence_no,
        )


def sweep_payloads(
    target: str,
    payload_start: int,
    payload_stop: int,
    payload_step: int,
    probe_count: int,
    timeout: float,
    executor: ProbeExecutor | None = None,
) -> list[dict[str, object]]:
    """Run a progressive PMTU sweep."""

    active_executor = executor or LinuxPingExecutor()
    results: list[dict[str, object]] = []
    sequence = 1
    for payload_size in range(payload_start, payload_stop + 1, payload_step):
        for _ in range(probe_count):
            result = active_executor.run_probe(target, payload_size, timeout, sequence)
            payload_record = asdict(result)
            payload_record["created_at"] = payload_record.get("created_at") or datetime.now(timezone.utc).isoformat()
            results.append(payload_record)
            sequence += 1
    return results


def infer_largest_successful_payload(probes: list[dict[str, object]]) -> int | None:
    """Return the largest successful payload size from the probe set."""

    successful_payloads = [int(probe["payload_size"]) for probe in probes if probe["success"]]
    return max(successful_payloads) if successful_payloads else None
