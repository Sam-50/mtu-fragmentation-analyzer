"""Demo script for running a single analysis from the command line."""

from __future__ import annotations

import argparse
import json

from app.schemas import AnalysisRequest
from app.services.analysis import run_analysis


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a PMTU and fragmentation analysis.")
    parser.add_argument("target", help="Target host or IP address")
    parser.add_argument("--payload-start", type=int, default=1200)
    parser.add_argument("--payload-stop", type=int, default=1472)
    parser.add_argument("--payload-step", type=int, default=16)
    parser.add_argument("--probe-count", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()

    request = AnalysisRequest(
        target=args.target,
        payload_start=args.payload_start,
        payload_stop=args.payload_stop,
        payload_step=args.payload_step,
        probe_count=args.probe_count,
        timeout=args.timeout,
    )
    result = run_analysis(request)
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
