"""Comprehensive test suite for SolarSaathi.
Verifies all functional, database, API, calculations, offline-resilience,
and structural acceptance criteria.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import database
import requests
import solar_agent


class TestSolarSaathi(unittest.TestCase):
    def setUp(self):
        self.app = app.app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_01_required_files_exist(self):
        """Verify all core project files exist in the project root."""
        root = Path(__file__).resolve().parent
        required = [
            root / "app.py",
            root / "solar_agent.py",
            root / "database.py",
            root / "requirements.txt",
            root / "README.md",
            root / ".gitignore",
            root / "static" / "index.html",
            root / "static" / "style.css",
            root / "static" / "script.js",
            root / "static" / "chart.min.js",
            root / "static" / "rooftop-solar.jpg",
            root / "static" / "logo.png",
            root / "static" / "favicon.png",
            root / "static" / "favicon.ico",
        ]
        for f in required:
            self.assertTrue(f.exists(), f"Missing required file: {f}")
            self.assertGreater(f.stat().st_size, 0, f"File is empty: {f}")

    def test_02_health_endpoint(self):
        """Verify GET /api/health returns 200 with expected JSON."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("app"), "SolarSaathi")
        self.assertEqual(data.get("database"), "connected")

    def test_03_index_page(self):
        """Verify GET / serves HTML containing key anchors and sections."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        res.close()
        self.assertIn("SolarSaathi", html)
        self.assertIn("id=\"top\"", html)
        self.assertIn("id=\"calculator\"", html)
        self.assertIn("id=\"how-it-works\"", html)
        self.assertIn("id=\"why-solar\"", html)
        self.assertIn("id=\"analytics\"", html)
        self.assertIn("id=\"faqs\"", html)
        self.assertIn("id=\"financial-disclaimer\"", html)
        self.assertIn("id=\"data-disclaimer\"", html)
        self.assertIn("https://www.myscheme.gov.in/schemes/pmsgmb", html)

    def test_04_calculate_valid_input(self):
        """Verify POST /api/calculate computes expected results and persists to SQLite."""
        payload = {
            "bill1": 2500,
            "bill2": 2800,
            "bill3": 2650,
            "roof_sqft": 500,
            "city": "Jaipur",
            "state": "Rajasthan",
        }
        res = self.client.post("/api/calculate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Check required fields
        self.assertIn("estimate_id", data)
        self.assertIsNotNone(data["estimate_id"])
        self.assertIn("potential", data)
        self.assertIn("financial", data)
        self.assertIn("environmental", data)
        self.assertIn("projections", data)
        self.assertIn("charts", data)
        self.assertIn("assumptions", data)

        # Numerical checks
        self.assertEqual(data["inputs"]["avg_monthly_bill"], 2650.0)
        self.assertEqual(data["potential"]["peak_sun_hours"], 5.6)
        self.assertGreater(data["potential"]["recommended_capacity_kw"], 0)
        self.assertGreater(data["financial"]["subsidy_inr"], 0)
        self.assertLessEqual(data["financial"]["subsidy_inr"], 78000.0)
        self.assertGreater(data["financial"]["annual_savings_inr"], 0)
        self.assertGreater(data["financial"]["monthly_savings_inr"], 0)
        self.assertGreater(data["financial"]["post_solar_bill_inr"], 0)
        self.assertLess(data["financial"]["post_solar_bill_inr"], data["inputs"]["avg_monthly_bill"])
        self.assertAlmostEqual(
            data["financial"]["post_solar_bill_inr"] + data["financial"]["monthly_savings_inr"],
            data["inputs"]["avg_monthly_bill"],
            places=1
        )
        self.assertGreater(data["environmental"]["co2_avoided_kg"], 0)
        self.assertGreater(data["environmental"]["coal_saved_kg"], 0)
        self.assertGreater(data["environmental"]["water_saved_litres"], 0)
        self.assertGreater(data["environmental"]["trees_equivalent"], 0)

    def test_05_calculate_invalid_inputs(self):
        """Verify validation errors on negative bills, zero roof, missing fields, invalid state."""
        # Negative bill
        res = self.client.post(
            "/api/calculate",
            json={"bill1": -100, "bill2": 200, "bill3": 300, "roof_sqft": 400, "state": "Delhi"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.get_json())

        # Zero roof area
        res = self.client.post(
            "/api/calculate",
            json={"bill1": 1000, "bill2": 1000, "bill3": 1000, "roof_sqft": 0, "state": "Delhi"},
        )
        self.assertEqual(res.status_code, 400)

        # Invalid State
        res = self.client.post(
            "/api/calculate",
            json={"bill1": 1000, "bill2": 1000, "bill3": 1000, "roof_sqft": 200, "state": "NonExistentState"},
        )
        self.assertEqual(res.status_code, 400)

        # Non-JSON
        res = self.client.post("/api/calculate", data="not a json", content_type="text/plain")
        self.assertEqual(res.status_code, 400)

    def test_06_database_persistence_and_retrieval(self):
        """Verify estimates endpoint returns persisted calculations in descending order."""
        res = self.client.get("/api/estimates")
        self.assertEqual(res.status_code, 200)
        records = res.get_json()
        self.assertIsInstance(records, list)
        self.assertGreaterEqual(len(records), 1)
        # Verify descending order of ID
        ids = [r["id"] for r in records]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_07_subsidy_calculation_logic(self):
        """Verify tiered PM Surya Ghar subsidy rules across sizes."""
        # 0.5 kW
        self.assertEqual(solar_agent.calculate_pm_surya_ghar_subsidy(0.5), 15000.0)
        # 1.0 kW
        self.assertEqual(solar_agent.calculate_pm_surya_ghar_subsidy(1.0), 30000.0)
        # 1.5 kW
        self.assertEqual(solar_agent.calculate_pm_surya_ghar_subsidy(1.5), 45000.0)
        # 2.0 kW
        self.assertEqual(solar_agent.calculate_pm_surya_ghar_subsidy(2.0), 60000.0)
        # 2.5 kW
        self.assertEqual(solar_agent.calculate_pm_surya_ghar_subsidy(2.5), 69000.0)
        # 3.0 kW
        self.assertEqual(solar_agent.calculate_pm_surya_ghar_subsidy(3.0), 78000.0)
        # 5.0 kW (capped at 78,000)
        self.assertEqual(solar_agent.calculate_pm_surya_ghar_subsidy(5.0), 78000.0)

    def test_08_insolation_benchmarks_all_36_states_and_uts(self):
        """Verify all 28 states and 8 union territories map to valid insolation values."""
        self.assertEqual(len(solar_agent.REGIONAL_INSOLATION_BENCHMARKS), 36)
        for state, psh in solar_agent.REGIONAL_INSOLATION_BENCHMARKS.items():
            self.assertGreaterEqual(psh, 4.0)
            self.assertLessEqual(psh, 6.0)

    def test_09_offline_resilience_open_meteo(self):
        """Verify calculator operates gracefully when Open-Meteo raises a network error."""
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Offline")):
            res = solar_agent.solar_potential_tool(
                city="Jaipur",
                usable_roof_sqft=500.0,
                state="Rajasthan",
                avg_monthly_bill=2500.0,
            )
            self.assertIn("Sensor offline", res["live_weather_note"])
            self.assertGreater(res["recommended_capacity_kw"], 0)
            self.assertGreater(res["monthly_generation_kwh"], 0)

    def test_10_strands_agent_instantiated(self):
        """Verify Strands Agent object is instantiated without requiring AWS credentials."""
        self.assertIsNotNone(solar_agent.solar_saathi_agent)
        self.assertEqual(type(solar_agent.solar_saathi_agent).__name__, "Agent")


if __name__ == "__main__":
    unittest.main()
