"""Small SQLite persistence layer for the 50% milestone.

The default database is SQLite so the project runs locally with one command.
The schema and repository functions are deliberately isolated so PostgreSQL
can be introduced later without changing the optimization engine.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("SHELTER_DB_PATH", BASE_DIR / "data" / "shelter.db"))


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS affected_groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                people INTEGER NOT NULL CHECK (people >= 0),
                priority INTEGER NOT NULL CHECK (priority >= 1),
                special_requirements TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS shelters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                capacity INTEGER NOT NULL CHECK (capacity >= 0),
                current_occupancy INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'available',
                facilities TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS optimization_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                objective_value REAL NOT NULL,
                total_people INTEGER NOT NULL,
                allocated_people INTEGER NOT NULL,
                unallocated_people INTEGER NOT NULL,
                total_travel_distance REAL NOT NULL,
                average_travel_distance REAL NOT NULL,
                runtime_ms REAL NOT NULL,
                result_json TEXT NOT NULL
            );
            """
        )


def seed_if_empty(groups: list[dict[str, Any]], shelters: list[dict[str, Any]]) -> bool:
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM affected_groups").fetchone()[0]
        if count:
            return False
        for g in groups:
            conn.execute(
                "INSERT INTO affected_groups VALUES (?, ?, ?, ?, ?, ?, ?)",
                (g["id"], g["name"], g["latitude"], g["longitude"], g["people"],
                 g["priority"], json.dumps(g.get("special_requirements", []))),
            )
        for s in shelters:
            conn.execute(
                "INSERT INTO shelters VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (s["id"], s["name"], s["latitude"], s["longitude"], s["capacity"],
                 s.get("current_occupancy", 0), s.get("status", "available"),
                 json.dumps(s.get("facilities", []))),
            )
    return True


def list_groups() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM affected_groups ORDER BY name").fetchall()
    return [{**dict(r), "special_requirements": json.loads(r["special_requirements"])} for r in rows]


def list_shelters() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM shelters ORDER BY name").fetchall()
    return [{**dict(r), "facilities": json.loads(r["facilities"])} for r in rows]


def insert_group(data: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO affected_groups VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data["id"], data["name"], data["latitude"], data["longitude"], data["people"],
             data.get("priority", 1), json.dumps(data.get("special_requirements", []))),
        )


def insert_shelter(data: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO shelters VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (data["id"], data["name"], data["latitude"], data["longitude"], data["capacity"],
             data.get("current_occupancy", 0), data.get("status", "available"),
             json.dumps(data.get("facilities", []))),
        )


def update_shelter_status(shelter_id: str, status: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("UPDATE shelters SET status=? WHERE id=?", (status, shelter_id))
        return cur.rowcount > 0


def save_run(result: dict[str, Any]) -> int:
    m = result["metrics"]
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO optimization_runs
            (status, objective_value, total_people, allocated_people, unallocated_people,
             total_travel_distance, average_travel_distance, runtime_ms, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (result["status"], m["objective_value"], m["total_people"], m["allocated_people"],
             m["unallocated_people"], m["total_travel_distance"], m["average_travel_distance"],
             m["runtime_ms"], json.dumps(result)),
        )
        return int(cur.lastrowid)


def list_runs() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, created_at, status, total_people, allocated_people, unallocated_people, "
            "average_travel_distance, runtime_ms FROM optimization_runs ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_run(run_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM optimization_runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        return None
    result = json.loads(row["result_json"])
    result["run_id"] = run_id
    result["created_at"] = row["created_at"]
    return result
