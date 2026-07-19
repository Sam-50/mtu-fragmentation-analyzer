"""SQLite persistence helpers."""

from __future__ import annotations

from contextlib import contextmanager
import json
import sqlite3
from typing import Any, Iterator

from app.config import settings


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a configured database connection."""

    connection = _connect()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    """Create the database schema when it does not already exist."""

    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                target_ip TEXT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                largest_successful_payload INTEGER,
                inferred_path_mtu INTEGER,
                recommended_mtu INTEGER,
                recommended_mss INTEGER,
                summary_json TEXT NOT NULL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS probes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                payload_size INTEGER NOT NULL,
                mtu_estimate INTEGER NOT NULL,
                success INTEGER NOT NULL,
                rtt_ms REAL,
                error_type TEXT,
                detail TEXT,
                method TEXT NOT NULL,
                sequence_no INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                probe_count INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                loss_rate REAL NOT NULL,
                avg_rtt_ms REAL,
                min_rtt_ms REAL,
                max_rtt_ms REAL,
                throughput_kbps REAL,
                jitter_ms REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                likely_issue TEXT NOT NULL,
                confidence TEXT NOT NULL,
                heuristic INTEGER NOT NULL,
                explanation TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                detail TEXT NOT NULL,
                value TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
            );
            """
        )


def insert_run(run: dict[str, Any]) -> int:
    """Persist a top-level analysis run and return its id."""

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO analysis_runs (
                target,
                target_ip,
                created_at,
                status,
                largest_successful_payload,
                inferred_path_mtu,
                recommended_mtu,
                recommended_mss,
                summary_json,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run["target"],
                run.get("target_ip"),
                run["created_at"],
                run["status"],
                run.get("largest_successful_payload"),
                run.get("inferred_path_mtu"),
                run.get("recommended_mtu"),
                run.get("recommended_mss"),
                json.dumps(run["summary"]),
                run.get("notes"),
            ),
        )
        return int(cursor.lastrowid)


def insert_probe(run_id: int, probe: dict[str, Any]) -> None:
    """Persist a single probe result."""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO probes (
                run_id, payload_size, mtu_estimate, success, rtt_ms, error_type,
                detail, method, sequence_no, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                probe["payload_size"],
                probe["mtu_estimate"],
                int(probe["success"]),
                probe.get("rtt_ms"),
                probe.get("error_type"),
                probe.get("detail"),
                probe["method"],
                probe["sequence_no"],
                probe["created_at"],
            ),
        )


def insert_measurement(run_id: int, measurement: dict[str, Any]) -> None:
    """Persist measurement summary."""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO measurements (
                run_id, probe_count, success_count, loss_rate, avg_rtt_ms, min_rtt_ms,
                max_rtt_ms, throughput_kbps, jitter_ms, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                measurement["probe_count"],
                measurement["success_count"],
                measurement["loss_rate"],
                measurement.get("avg_rtt_ms"),
                measurement.get("min_rtt_ms"),
                measurement.get("max_rtt_ms"),
                measurement.get("throughput_kbps"),
                measurement.get("jitter_ms"),
                measurement["created_at"],
            ),
        )


def insert_analysis(run_id: int, analysis: dict[str, Any]) -> None:
    """Persist heuristic analysis output."""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO analyses (
                run_id, likely_issue, confidence, heuristic, explanation,
                evidence_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                analysis["likely_issue"],
                analysis["confidence"],
                int(analysis["heuristic"]),
                analysis["explanation"],
                json.dumps(analysis["evidence"]),
                analysis["created_at"],
            ),
        )


def insert_recommendation(run_id: int, recommendation: dict[str, Any]) -> None:
    """Persist a recommendation item."""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO recommendations (
                run_id, category, title, detail, value, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                recommendation["category"],
                recommendation["title"],
                recommendation["detail"],
                recommendation.get("value"),
                recommendation["created_at"],
            ),
        )


def fetch_run(run_id: int) -> sqlite3.Row | None:
    """Fetch a single run."""

    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM analysis_runs WHERE id = ?",
            (run_id,),
        ).fetchone()


def fetch_run_related(table: str, run_id: int) -> list[sqlite3.Row]:
    """Fetch rows related to a run from a known table."""

    if table not in {"probes", "measurements", "analyses", "recommendations"}:
        raise ValueError(f"Unsupported table: {table}")

    with get_connection() as connection:
        return connection.execute(
            f"SELECT * FROM {table} WHERE run_id = ? ORDER BY id ASC",
            (run_id,),
        ).fetchall()


def fetch_recent_runs(limit: int = 20) -> list[sqlite3.Row]:
    """Fetch recent analysis runs."""

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT * FROM analysis_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
