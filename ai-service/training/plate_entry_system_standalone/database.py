"""
database.py
------------
SQLite-backed vehicle registry + entry log for the college gate system.

Tables
------
vehicles(plate_number PK, owner_name, role, department, vehicle_type, active)
entry_logs(id PK, plate_number, matched_plate, status, confidence, timestamp)

Handles the fact that OCR is never 100% perfect: check_plate() first
tries an exact match, then falls back to a fuzzy match against all
registered plates so a single misread character (O/0, I/1, S/5, B/8)
doesn't wrongly deny a legitimate vehicle.
"""

import sqlite3
import difflib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "vehicles.db"


@dataclass
class VehicleRecord:
    plate_number: str
    owner_name: str
    role: str            # student / staff / faculty / visitor
    department: str
    vehicle_type: str    # car / bike
    active: bool


@dataclass
class CheckResult:
    allowed: bool
    matched_plate: Optional[str]
    record: Optional[VehicleRecord]
    similarity: float     # 1.0 = exact match, <1.0 = fuzzy match


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            plate_number TEXT PRIMARY KEY,
            owner_name   TEXT NOT NULL,
            role         TEXT NOT NULL,
            department   TEXT,
            vehicle_type TEXT,
            active       INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entry_logs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number   TEXT,       -- raw OCR output
            matched_plate  TEXT,       -- plate matched in DB, if any
            status         TEXT,       -- ALLOWED / DENIED
            confidence     REAL,
            timestamp      TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_vehicle(plate_number: str, owner_name: str, role: str,
                 department: str = "", vehicle_type: str = "car", active: bool = True):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO vehicles (plate_number, owner_name, role, department, vehicle_type, active) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (plate_number.upper().replace(" ", ""), owner_name, role, department, vehicle_type, int(active)),
    )
    conn.commit()
    conn.close()


def remove_vehicle(plate_number: str):
    conn = get_connection()
    conn.execute("DELETE FROM vehicles WHERE plate_number = ?", (plate_number.upper().replace(" ", ""),))
    conn.commit()
    conn.close()


def _all_active_plates(conn) -> list[str]:
    rows = conn.execute("SELECT plate_number FROM vehicles WHERE active = 1").fetchall()
    return [r["plate_number"] for r in rows]


def check_plate(ocr_text: str, fuzzy_threshold: float = 0.82) -> CheckResult:
    """
    Look up an OCR-read plate against the registry.

    1. Exact match (after normalizing case/spaces) -> allowed, similarity 1.0
    2. Otherwise, fuzzy match against all active plates using difflib's
       SequenceMatcher ratio. If the best match clears fuzzy_threshold,
       it's still allowed (handles 1-2 character OCR slips) but flagged
       with a similarity < 1.0 so staff can spot-check it in the logs.
    3. No good match -> denied.
    """
    clean = ocr_text.upper().replace(" ", "")
    conn = get_connection()

    row = conn.execute("SELECT * FROM vehicles WHERE plate_number = ? AND active = 1", (clean,)).fetchone()
    if row:
        conn.close()
        record = VehicleRecord(row["plate_number"], row["owner_name"], row["role"],
                                row["department"], row["vehicle_type"], bool(row["active"]))
        return CheckResult(allowed=True, matched_plate=row["plate_number"], record=record, similarity=1.0)

    candidates = _all_active_plates(conn)
    best_plate, best_ratio = None, 0.0
    for cand in candidates:
        ratio = difflib.SequenceMatcher(None, clean, cand).ratio()
        if ratio > best_ratio:
            best_plate, best_ratio = cand, ratio

    if best_plate and best_ratio >= fuzzy_threshold:
        row = conn.execute("SELECT * FROM vehicles WHERE plate_number = ?", (best_plate,)).fetchone()
        conn.close()
        record = VehicleRecord(row["plate_number"], row["owner_name"], row["role"],
                                row["department"], row["vehicle_type"], bool(row["active"]))
        return CheckResult(allowed=True, matched_plate=best_plate, record=record, similarity=best_ratio)

    conn.close()
    return CheckResult(allowed=False, matched_plate=None, record=None, similarity=best_ratio)


def log_entry(raw_ocr_text: str, result: CheckResult):
    conn = get_connection()
    conn.execute(
        "INSERT INTO entry_logs (plate_number, matched_plate, status, confidence, timestamp) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            raw_ocr_text,
            result.matched_plate,
            "ALLOWED" if result.allowed else "DENIED",
            result.similarity,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Bootstrap the DB with a couple of sample vehicles so you can test
    # end-to-end immediately. Edit / add real records with add_vehicle.py.
    init_db()
    add_vehicle("MH12AB1234", "Rahul Sharma", "student", "CSE", "car")
    add_vehicle("MP09XY5678", "Dr. Neha Verma", "faculty", "ECE", "car")
    add_vehicle("DL8CAF9999", "Amit Singh", "staff", "Admin", "bike")
    print(f"Database initialized at {DB_PATH} with sample vehicles.")
