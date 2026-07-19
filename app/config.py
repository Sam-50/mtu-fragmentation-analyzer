"""Application configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(slots=True)
class Settings:
    """Runtime settings for the analyzer."""

    app_name: str = "Intelligent MTU Discovery and IP Fragmentation Mitigation System"
    database_path: Path = BASE_DIR / "data" / "mtu_analyzer.db"
    export_path: Path = BASE_DIR / "data" / "exports"
    default_probe_timeout: float = 2.0
    default_probe_count: int = 3
    default_payload_start: int = 1200
    default_payload_stop: int = 1472
    default_payload_step: int = 16
    tcp_ipv4_header_bytes: int = 40
    tcp_ipv6_header_bytes: int = 60
    ping_binary: str = os.getenv("PING_BINARY", "ping")
    scapy_enabled: bool = os.getenv("ENABLE_SCAPY", "0") == "1"


settings = Settings()
settings.database_path.parent.mkdir(parents=True, exist_ok=True)
settings.export_path.mkdir(parents=True, exist_ok=True)
