"""Database module for SolarSaathi.

Manages SQLite storage for rooftop solar estimates with parameterized queries,
safe connection handling, and migration/initialization logic.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Ensure database path is always resolved relative to this file's directory
DB_PATH = Path(__file__).resolve().parent / "solarsaathi.db"


def get_connection() -> sqlite3.Connection:
    """Return a configured SQLite connection with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency and reliability
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initialize SQLite database and ensure tables exist."""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS estimates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        bill1 REAL NOT NULL,
        bill2 REAL NOT NULL,
        bill3 REAL NOT NULL,
        avg_bill REAL NOT NULL,
        roof_sqft REAL NOT NULL,
        recommended_kw REAL NOT NULL,
        gross_cost_inr REAL NOT NULL,
        subsidy_inr REAL NOT NULL,
        net_investment_inr REAL NOT NULL,
        monthly_savings_inr REAL NOT NULL,
        post_solar_bill_inr REAL NOT NULL,
        annual_savings_inr REAL NOT NULL,
        payback_years REAL,
        co2_avoided_kg REAL NOT NULL,
        coal_saved_kg REAL NOT NULL,
        trees_equivalent INTEGER NOT NULL,
        water_saved_litres REAL NOT NULL,
        live_weather_note TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    conn = get_connection()
    try:
        with conn:
            conn.execute(create_table_query)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_estimates_created_at ON estimates (created_at DESC);")
        logger.info("Database initialized successfully at %s", DB_PATH)
    except sqlite3.Error as e:
        logger.error("Failed to initialize database: %s", e)
        raise
    finally:
        conn.close()


def save_estimate(record: Dict[str, Any]) -> int:
    """Save a validated estimate record into SQLite. Returns the inserted row ID."""
    insert_query = """
    INSERT INTO estimates (
        city, state, bill1, bill2, bill3, avg_bill, roof_sqft,
        recommended_kw, gross_cost_inr, subsidy_inr, net_investment_inr,
        monthly_savings_inr, post_solar_bill_inr, annual_savings_inr,
        payback_years, co2_avoided_kg, coal_saved_kg, trees_equivalent,
        water_saved_litres, live_weather_note
    ) VALUES (
        :city, :state, :bill1, :bill2, :bill3, :avg_bill, :roof_sqft,
        :recommended_kw, :gross_cost_inr, :subsidy_inr, :net_investment_inr,
        :monthly_savings_inr, :post_solar_bill_inr, :annual_savings_inr,
        :payback_years, :co2_avoided_kg, :coal_saved_kg, :trees_equivalent,
        :water_saved_litres, :live_weather_note
    );
    """
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(insert_query, record)
            row_id = cursor.lastrowid
            if row_id is None:
                raise RuntimeError("Failed to obtain inserted row ID.")
            return row_id
    except sqlite3.Error as e:
        logger.error("Error saving estimate: %s", e)
        raise RuntimeError("Could not save calculation to local database.") from e
    finally:
        conn.close()


def get_recent_estimates(limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve the most recent calculation records in descending order."""
    safe_limit = max(1, min(limit, 50))  # bounded limit
    query = """
    SELECT
        id, city, state, bill1, bill2, bill3, avg_bill, roof_sqft,
        recommended_kw, gross_cost_inr, subsidy_inr, net_investment_inr,
        monthly_savings_inr, post_solar_bill_inr, annual_savings_inr,
        payback_years, co2_avoided_kg, coal_saved_kg, trees_equivalent,
        water_saved_litres, live_weather_note, created_at
    FROM estimates
    ORDER BY id DESC
    LIMIT ?;
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (safe_limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error("Error fetching recent estimates: %s", e)
        return []
    finally:
        conn.close()


def get_estimate_by_id(estimate_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single estimate by ID."""
    query = "SELECT * FROM estimates WHERE id = ?;"
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (estimate_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error("Error fetching estimate %s: %s", estimate_id, e)
        return None
    finally:
        conn.close()
