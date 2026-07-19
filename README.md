# Intelligent MTU Discovery and IP Fragmentation Mitigation System

This project was part of my  Internetworking with TCP/IP course. It measures Path MTU behavior, records fragmentation-related symptoms, estimates RTT and packet loss, applies conservative TCP symptom heuristics, and produces plain-language recommendations such as a likely safe MTU and a candidate TCP MSS clamp value.

The design focuses on practical local execution in WSL2 Ubuntu. Instead of relying only on raw sockets, the default probing path uses Linux `ping` via `subprocess`, because this is more reliable in WSL2 and still demonstrates core TCP/IP concepts such as DF semantics, IP fragmentation pressure, PMTUD behavior, and the impact of blocked ICMP feedback.

## Networking Problem Being Solved

Path MTU issues appear when a sender transmits packets larger than what some link on the end-to-end path can carry without fragmentation. In modern networks, this often happens because of:

- VPN or IPsec overhead reducing effective payload size
- MPLS or backbone path mismatches
- PPPoE or tunnel encapsulation
- Firewalls or routers blocking ICMP "Fragmentation Needed" messages
- Mixed access networks with inconsistent path behavior

These problems can create symptoms that look like general poor network quality:

- stalled TCP sessions
- dropped packets
- slow file transfers
- poor video or VoIP quality
- broken application flows after data size thresholds are crossed

This project connects those symptoms to Internetworking with TCP/IP concepts:

- IP fragmentation and reassembly
- Path MTU Discovery (PMTUD)
- ICMP "Fragmentation Needed"
- TCP MSS negotiation and MSS clamping
- retransmission-like stall patterns
- the difference between probable MTU issues and ordinary congestion
- end-to-end behavior across heterogeneous internetworks

## Architecture Overview

The application uses a small FastAPI backend with SQLite persistence and a local dashboard:

- `app/services/pmtud.py`: target validation, payload sweeps, WSL2-safe `ping` probing, MTU/MSS helpers
- `app/services/measurement.py`: RTT, loss, jitter, and simple throughput approximation
- `app/services/tcp_analysis.py`: conservative heuristic findings
- `app/services/recommendations.py`: safe MTU, MSS clamp, and probable-cause recommendations
- `app/services/reporting.py`: JSON, CSV, and human-readable report generation
- `app/routes/api.py`: machine-readable API
- `app/routes/dashboard.py`: local dashboard pages
- `app/db.py`: SQLite schema and persistence logic

## Project Structure

```text
mtu-fragmentation-analyzer/
  app/
    __init__.py
    main.py
    config.py
    db.py
    models.py
    schemas.py
    services/
      __init__.py
      analysis.py
      pmtud.py
      measurement.py
      tcp_analysis.py
      recommendations.py
      reporting.py
    routes/
      __init__.py
      api.py
      dashboard.py
    templates/
      index.html
      results.html
    static/
      styles.css
  tests/
    conftest.py
    test_api.py
    test_recommendations.py
  scripts/
    demo_run.py
  data/
    sample_run.json
  README.md
  requirements.txt
  .gitignore
```

## Setup in WSL2 Ubuntu

Use WSL2 Ubuntu rather than native Windows Python for the main demo workflow.

1. Open your project inside WSL2 Ubuntu.
2. Install system prerequisites:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip iputils-ping
```

3. Create and activate a virtual environment:

```bash
cd mtu-fragmentation-analyzer
python3 -m venv .venv
source .venv/bin/activate
```

4. Install Python dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Running the App

Start the FastAPI server from WSL2:

```bash
cd mtu-fragmentation-analyzer
uvicorn app.main:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

The dashboard lets you:

- enter a target host or IP
- launch an MTU analysis run
- inspect probe history
- view MTU success and RTT charts
- review heuristic findings and recommendations
- export JSON, CSV, and text summaries

## API Usage

Example analysis request:

```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"target":"8.8.8.8","payload_start":1200,"payload_stop":1472,"payload_step":16,"probe_count":2,"timeout":2.0}'
```

Example CLI demo:

```bash
python scripts/demo_run.py 8.8.8.8 --payload-start 1200 --payload-stop 1472 --payload-step 16 --probe-count 2
```

## Testing

Run tests with:

```bash
cd mtu-fragmentation-analyzer
pytest
```

The tests mock probe execution, so they do not require raw socket access or live network connectivity.

## Reporting and Export

For each run, the system can:

- return a JSON report
- export probe records to CSV
- generate a human-readable summary for a university demo

CSV exports are written under `data/exports/`.

## WSL2 and Raw Socket Limitations

This project intentionally avoids overclaiming low-level visibility in WSL2.

- Raw packet crafting may be restricted or inconsistent depending on WSL2 networking mode, privileges, and local firewall behavior.
- Scapy is included for future extension, but the default implementation uses Linux `ping` through `subprocess` because it is more dependable for a first working version.
- ICMP filtering, host policy, or cloud edge filtering may cause silent probe loss that looks similar to congestion or PMTUD black holes.
- The TCP analyzer is heuristic. It highlights patterns consistent with fragmentation trouble, but it does not prove router misconfiguration or distinguish every case from congestion.

## What Is Measured vs Heuristic

Measured facts:

- whether each probe succeeded or failed
- RTT for probes that returned timing data
- loss rate across repeated probes
- the largest observed payload that succeeded without fragmentation

Heuristic conclusions:

- likely PMTU black-hole behavior
- likely tunnel or VPN overhead
- likely size-threshold stall patterns
- likely difference between size-related failure and generic congestion/filtering

Use terms such as "likely", "consistent with", and "possible" when presenting results.

## Future Improvements

- add optional Scapy-based enhanced probing for environments where raw sockets are stable
- support IPv6 PMTUD and IPv6-specific MSS guidance
- add traceroute correlation for bottleneck localization
- add live TCP capture correlation with retransmission counts
- add richer historical comparison dashboards
- add authentication and multi-user run management

## Screenshots

Add screenshots for your final report here:

- `docs/screenshots/dashboard-home.png`
- `docs/screenshots/run-results.png`

## Notes for University Demo

Good demo targets:

- `8.8.8.8`
- a reachable campus server
- a VPN-connected endpoint to demonstrate reduced MTU

During the demo, explain that:

- PMTUD depends on DF behavior plus ICMP feedback
- blocked ICMP can create black-hole behavior
- MSS clamping is a practical mitigation for TCP traffic
- the system stores evidence separately from heuristic interpretation
