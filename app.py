"""Flask backend application for SolarSaathi.

Provides RESTful API endpoints for solar potential calculation,
health checks, and recent estimate history with SQLite persistence.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import database
import solar_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("solarsaathi")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
# 1MB maximum payload size limit
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

# Restrict CORS to local development origins
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5000",
                "http://127.0.0.1:5000",
                "http://localhost:5001",
                "http://127.0.0.1:5001",
            ],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    },
)

# Supported 28 States and 8 Union Territories
VALID_STATES = {
    # 28 States
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    # 8 Union Territories
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
}

# Create case-insensitive lookup
STATE_LOOKUP = {s.lower(): s for s in VALID_STATES}


def validate_number(value: Any, name: str, min_val: float = 0.0, max_val: float = 1e7) -> float:
    """Validate that input is a finite float within bounds."""
    if value is None:
        raise ValueError(f"Field '{name}' is required.")
    try:
        num = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Field '{name}' must be a valid numeric value.")

    if math.isnan(num) or math.isinf(num):
        raise ValueError(f"Field '{name}' cannot be NaN or infinity.")
    if num < min_val:
        raise ValueError(f"Field '{name}' must be at least {min_val}.")
    if num > max_val:
        raise ValueError(f"Field '{name}' exceeds reasonable threshold ({max_val}).")
    return num


# ==============================================================================
# Routes
# ==============================================================================
@app.route("/")
def index():
    """Serve the single-page application frontend."""
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint confirming application and database availability."""
    try:
        # Verify SQLite connection
        recent = database.get_recent_estimates(1)
        db_status = "connected"
    except Exception as e:
        logger.error("Health check failed for database: %s", e)
        db_status = "unhealthy"

    return jsonify({
        "status": "ok" if db_status == "connected" else "degraded",
        "app": "SolarSaathi",
        "version": "1.0.0",
        "database": db_status,
    }), 200


@app.route("/api/calculate", methods=["POST"])
def calculate():
    """Perform deterministic solar assessment and persist result in SQLite."""
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON."}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON format."}), 400

    # 1. Input Validation
    try:
        bill1 = validate_number(data.get("bill1"), "bill1", min_val=0.0, max_val=500000.0)
        bill2 = validate_number(data.get("bill2"), "bill2", min_val=0.0, max_val=500000.0)
        bill3 = validate_number(data.get("bill3"), "bill3", min_val=0.0, max_val=500000.0)
        roof_sqft = validate_number(data.get("roof_sqft"), "roof_sqft", min_val=10.0, max_val=100000.0)

        raw_state = str(data.get("state", "")).strip()
        if not raw_state:
            return jsonify({"error": "Please select a valid Indian State or Union Territory."}), 400

        normalized_state = STATE_LOOKUP.get(raw_state.lower())
        if not normalized_state:
            return jsonify({
                "error": f"State '{raw_state}' is not recognized. Please choose from supported Indian states and UTs."
            }), 400

        raw_city = str(data.get("city", "")).strip()
        # If city is blank, default to representative city for that state
        city = raw_city if raw_city else solar_agent.REPRESENTATIVE_CITIES.get(normalized_state, normalized_state)

    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception as e:
        logger.error("Unexpected error during input parsing: %s", e)
        return jsonify({"error": "Invalid request parameters."}), 400

    # 2. Run Deterministic Solar Calculation Pipeline
    try:
        result = solar_agent.run_solar_pipeline(
            bill1=bill1,
            bill2=bill2,
            bill3=bill3,
            roof_sqft=roof_sqft,
            city=city,
            state=normalized_state,
        )
    except Exception as pipe_err:
        logger.error("Calculation pipeline error: %s", pipe_err, exc_info=True)
        return jsonify({"error": "Failed to calculate solar estimates. Please check inputs."}), 500

    # 3. Persist Calculation Record to SQLite
    try:
        rec: Dict[str, Any] = {
            "city": result["inputs"]["city"],
            "state": result["inputs"]["state"],
            "bill1": result["inputs"]["bill1"],
            "bill2": result["inputs"]["bill2"],
            "bill3": result["inputs"]["bill3"],
            "avg_bill": result["inputs"]["avg_monthly_bill"],
            "roof_sqft": result["inputs"]["roof_sqft"],
            "recommended_kw": result["potential"]["recommended_capacity_kw"],
            "gross_cost_inr": result["financial"]["gross_cost_inr"],
            "subsidy_inr": result["financial"]["subsidy_inr"],
            "net_investment_inr": result["financial"]["net_investment_inr"],
            "monthly_savings_inr": result["financial"]["monthly_savings_inr"],
            "post_solar_bill_inr": result["financial"]["post_solar_bill_inr"],
            "annual_savings_inr": result["financial"]["annual_savings_inr"],
            "payback_years": result["financial"]["payback_years"],
            "co2_avoided_kg": result["environmental"]["co2_avoided_kg"],
            "coal_saved_kg": result["environmental"]["coal_saved_kg"],
            "trees_equivalent": result["environmental"]["trees_equivalent"],
            "water_saved_litres": result["environmental"]["water_saved_litres"],
            "live_weather_note": result["live_weather_note"],
        }
        estimate_id = database.save_estimate(rec)
        result["estimate_id"] = estimate_id
    except Exception as db_err:
        logger.error("Database save failed: %s", db_err)
        # Even if DB save encounters an issue, return calculation result with null id
        result["estimate_id"] = None

    return jsonify(result), 200


@app.route("/api/estimates", methods=["GET"])
def get_estimates():
    """Retrieve the 5 most recent calculation records."""
    try:
        limit = request.args.get("limit", default=5, type=int)
        records = database.get_recent_estimates(limit=limit)
        return jsonify(records), 200
    except Exception as e:
        logger.error("Failed to retrieve estimates: %s", e)
        return jsonify({"error": "Unable to fetch recent estimates."}), 500


# ==============================================================================
# Error Handlers
# ==============================================================================
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found."}), 404
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({"error": "Request payload too large (max 1MB)."}), 413


@app.errorhandler(500)
def server_error(e):
    logger.error("Internal Server Error: %s", e)
    return jsonify({"error": "An internal server error occurred."}), 500


# ==============================================================================
# Application Startup
# ==============================================================================
# Initialize SQLite table schema at module import / app startup
try:
    database.init_db()
    logger.info("SolarSaathi backend initialized successfully.")
except Exception as init_err:
    logger.critical("Database initialization failed on startup: %s", init_err)

if __name__ == "__main__":
    import os
    import socket

    port = int(os.environ.get("PORT", 5000))

    def is_port_bindable(p: int, h: str = "0.0.0.0") -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((h, p))
                return True
            except OSError:
                return False

    if port == 5000 and not is_port_bindable(5000):
        logger.warning(
            "⚠️  Port 5000 is occupied (commonly by macOS AirPlay Receiver). "
            "To run on port 5000: System Settings > General > AirDrop & AirPlay > AirPlay Receiver -> Turn Off. "
            "Automatically switching to port 5001 so the server can run immediately."
        )
        port = 5001

    logger.info("Starting SolarSaathi on http://localhost:%d", port)
    app.run(host="0.0.0.0", port=port, debug=True)
