"""Solar assessment logic and Strands Agent integration for SolarSaathi.

Implements modular Strands @tool functions and a deterministic calculation
pipeline for solar potential, PM Surya Ghar subsidy, financial ROI, and environmental impacts.
"""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import requests
from strands import Agent, tool

logger = logging.getLogger(__name__)

# ==============================================================================
# 7.1 Regional Solar-Insolation Benchmarks (Peak Sun Hours / day)
# ==============================================================================
# Fixed illustrative regional planning assumptions based on standard Indian solar atlas benchmarks.
REGIONAL_INSOLATION_BENCHMARKS: Dict[str, float] = {
    # Northern Region
    "Delhi": 4.9,
    "Haryana": 5.1,
    "Punjab": 5.0,
    "Rajasthan": 5.6,
    "Uttar Pradesh": 4.9,
    "Uttarakhand": 4.8,
    "Himachal Pradesh": 4.7,
    "Jammu and Kashmir": 4.6,
    "Ladakh": 5.8,
    "Chandigarh": 5.0,
    # Western & Central Region
    "Gujarat": 5.5,
    "Maharashtra": 5.2,
    "Goa": 4.9,
    "Madhya Pradesh": 5.3,
    "Chhattisgarh": 5.1,
    "Dadra and Nagar Haveli and Daman and Diu": 5.2,
    # Southern & Eastern Region
    "Bihar": 4.7,
    "Jharkhand": 4.8,
    "West Bengal": 4.6,
    "Odisha": 4.9,
    "Andhra Pradesh": 5.3,
    "Telangana": 5.2,
    "Karnataka": 5.3,
    "Tamil Nadu": 5.2,
    "Kerala": 4.7,
    "Puducherry": 5.1,
    "Lakshadweep": 5.0,
    "Andaman and Nicobar Islands": 4.5,
    # North-Eastern Region
    "Assam": 4.2,
    "Sikkim": 4.3,
    "Meghalaya": 4.1,
    "Tripura": 4.4,
    "Mizoram": 4.3,
    "Manipur": 4.4,
    "Nagaland": 4.2,
    "Arunachal Pradesh": 4.1,
}

DEFAULT_PEAK_SUN_HOURS: float = 4.8

# Representative cities for geocoding / fallback weather lookups
REPRESENTATIVE_CITIES: Dict[str, str] = {
    "Andaman and Nicobar Islands": "Port Blair",
    "Andhra Pradesh": "Visakhapatnam",
    "Arunachal Pradesh": "Itanagar",
    "Assam": "Guwahati",
    "Bihar": "Patna",
    "Chandigarh": "Chandigarh",
    "Chhattisgarh": "Raipur",
    "Dadra and Nagar Haveli and Daman and Diu": "Daman",
    "Delhi": "New Delhi",
    "Goa": "Panaji",
    "Gujarat": "Ahmedabad",
    "Haryana": "Gurugram",
    "Himachal Pradesh": "Shimla",
    "Jammu and Kashmir": "Srinagar",
    "Jharkhand": "Ranchi",
    "Karnataka": "Bengaluru",
    "Kerala": "Thiruvananthapuram",
    "Ladakh": "Leh",
    "Lakshadweep": "Kavaratti",
    "Madhya Pradesh": "Bhopal",
    "Maharashtra": "Mumbai",
    "Manipur": "Imphal",
    "Meghalaya": "Shillong",
    "Mizoram": "Aizawl",
    "Nagaland": "Kohima",
    "Odisha": "Bhubaneswar",
    "Puducherry": "Puducherry",
    "Punjab": "Amritsar",
    "Rajasthan": "Jaipur",
    "Sikkim": "Gangtok",
    "Tamil Nadu": "Chennai",
    "Telangana": "Hyderabad",
    "Tripura": "Agartala",
    "Uttar Pradesh": "Lucknow",
    "Uttarakhand": "Dehradun",
    "West Bengal": "Kolkata",
}

# Configurable technical and financial constants
DEFAULT_PERFORMANCE_RATIO: float = 0.80  # Accounts for inverter, temperature, soiling losses
DEFAULT_COST_PER_KW: float = 55000.0     # INR per kW installed gross cost benchmark
DEFAULT_TARIFF_PER_KWH: float = 7.5      # INR per kWh average residential slab tariff


# ==============================================================================
# Helper Calculation Functions
# ==============================================================================
def resolve_insolation(state: str, city: str = "") -> Tuple[float, str]:
    """Resolve peak sun hours per day from state benchmark, with fallback."""
    normalized_state = state.strip()
    if normalized_state in REGIONAL_INSOLATION_BENCHMARKS:
        return REGIONAL_INSOLATION_BENCHMARKS[normalized_state], normalized_state

    # Try case-insensitive matching
    for s, hours in REGIONAL_INSOLATION_BENCHMARKS.items():
        if s.lower() == normalized_state.lower():
            return hours, s

    # Fallback default
    logger.warning("State '%s' not found in benchmarks; using fallback %.1f", state, DEFAULT_PEAK_SUN_HOURS)
    return DEFAULT_PEAK_SUN_HOURS, normalized_state or "National Benchmark"


def fetch_open_meteo_weather(city: str, state: str = "") -> Tuple[str, Optional[float], Optional[float]]:
    """Attempt optional Open-Meteo geocoding and live solar irradiance lookup.

    Returns:
        (live_weather_note, direct_radiation_wm2, cloud_cover_pct)
    """
    search_query = city.strip()
    if not search_query and state:
        search_query = REPRESENTATIVE_CITIES.get(state, state)

    fallback_note = "Live Weather: Sensor offline (using regional insolation benchmark)."

    if not search_query:
        return fallback_note, None, None

    try:
        # Step 1: Geocoding lookup (timeout 2.5s)
        encoded_city = urllib.parse.quote(search_query)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1"
        geo_resp = requests.get(geo_url, timeout=2.5)

        if geo_resp.status_code != 200:
            return fallback_note, None, None

        geo_data = geo_resp.json()
        results = geo_data.get("results")
        if not results or len(results) == 0:
            return fallback_note, None, None

        first_match = results[0]
        lat = first_match.get("latitude")
        lon = first_match.get("longitude")
        matched_city = first_match.get("name", search_query)

        if lat is None or lon is None:
            return fallback_note, None, None

        # Step 2: Current direct radiation & cloud cover (timeout 2.5s)
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current=direct_radiation,cloud_cover"
        )
        weather_resp = requests.get(forecast_url, timeout=2.5)
        if weather_resp.status_code != 200:
            return fallback_note, None, None

        weather_data = weather_resp.json()
        current = weather_data.get("current", {})
        direct_rad = current.get("direct_radiation")
        cloud_cover = current.get("cloud_cover")

        if direct_rad is not None and cloud_cover is not None:
            rad_val = round(float(direct_rad), 1)
            cloud_val = round(float(cloud_cover), 1)
            note = (
                f"Live Climate: Current direct solar irradiance in {matched_city} "
                f"is {rad_val} W/m² with {cloud_val}% cloud cover."
            )
            return note, rad_val, cloud_val

        return fallback_note, None, None

    except Exception as e:
        logger.debug("Open-Meteo lookup failed or network offline: %s", e)
        return fallback_note, None, None


def calculate_pm_surya_ghar_subsidy(capacity_kw: float) -> float:
    """Calculate indicative PM Surya Ghar central financial assistance.

    Tiered structure:
    - 0 to 1 kW: ₹30,000 per kW (prorated for fractional capacity)
    - >1 to 2 kW: ₹30,000 per kW (prorated)
    - >2 to 3 kW: ₹18,000 per kW (prorated)
    - Above 3 kW: ₹0 additional assistance
    - Maximum standard residential subsidy ceiling: ₹78,000
    """
    if capacity_kw <= 0:
        return 0.0

    subsidy = 0.0

    # Slab 1: First 1 kW
    tier1 = min(capacity_kw, 1.0)
    subsidy += tier1 * 30000.0

    # Slab 2: Next 1 kW (1 to 2 kW)
    if capacity_kw > 1.0:
        tier2 = min(capacity_kw - 1.0, 1.0)
        subsidy += tier2 * 30000.0

    # Slab 3: Next 1 kW (2 to 3 kW)
    if capacity_kw > 2.0:
        tier3 = min(capacity_kw - 2.0, 1.0)
        subsidy += tier3 * 18000.0

    # Central subsidy ceiling
    return round(min(subsidy, 78000.0), 2)


# ==============================================================================
# 7.2 Tool 1 — solar_potential_tool
# ==============================================================================
@tool
def solar_potential_tool(
    city: str,
    usable_roof_sqft: float,
    state: str = "",
    avg_monthly_bill: float = 0.0,
    performance_ratio: float = DEFAULT_PERFORMANCE_RATIO,
) -> Dict[str, Any]:
    """Assess rooftop solar generation potential and recommend system capacity.

    Args:
        city: City or town name.
        usable_roof_sqft: Available shadow-free rooftop area in square feet.
        state: Indian State or Union Territory name.
        avg_monthly_bill: Optional average electricity bill (used to calibrate demand).
        performance_ratio: De-rating factor for system losses (default 0.80).

    Returns:
        Structured dictionary with recommended capacity, generation metrics, and live weather.
    """
    if usable_roof_sqft <= 0:
        raise ValueError("Rooftop area must be greater than zero.")

    peak_sun_hours, resolved_state = resolve_insolation(state, city)

    # Raw roof-based physical limit (rule of thumb: ~100 sq.ft per 1 kW)
    raw_roof_capacity_kw = round(usable_roof_sqft / 100.0, 2)

    # Calibration: cap capacity by likely household consumption to prevent recommending oversized systems
    if avg_monthly_bill > 0:
        offsettable_bill = avg_monthly_bill * 0.755  # Energy charges portion (~75.5%)
        estimated_monthly_units = offsettable_bill / DEFAULT_TARIFF_PER_KWH
        daily_units_needed = estimated_monthly_units / 30.0
        # Required kW to meet household demand under regional peak sun hours
        demand_capacity_kw = daily_units_needed / (peak_sun_hours * performance_ratio)
        # Size to comfortably cover energy demand, minimum 1.0 kW, capped by physical rooftop limit
        target_kw = max(1.0, round(demand_capacity_kw * 1.15, 1))
        recommended_capacity_kw = round(min(raw_roof_capacity_kw, target_kw), 2)
    else:
        recommended_capacity_kw = raw_roof_capacity_kw

    # Generation calculations
    monthly_generation_kwh = round(
        recommended_capacity_kw * peak_sun_hours * 30.0 * performance_ratio, 2
    )
    annual_generation_kwh = round(monthly_generation_kwh * 12.0, 2)

    # Optional live weather call
    live_note, direct_rad, cloud_cov = fetch_open_meteo_weather(city, state)

    return {
        "city": city.strip(),
        "state": resolved_state,
        "usable_roof_sqft": round(float(usable_roof_sqft), 1),
        "raw_roof_capacity_kw": raw_roof_capacity_kw,
        "recommended_capacity_kw": recommended_capacity_kw,
        "peak_sun_hours": peak_sun_hours,
        "performance_ratio": performance_ratio,
        "monthly_generation_kwh": monthly_generation_kwh,
        "annual_generation_kwh": annual_generation_kwh,
        "live_weather_note": live_note,
        "direct_radiation_wm2": direct_rad,
        "cloud_cover_pct": cloud_cov,
    }


# ==============================================================================
# 7.3 Tool 2 — financial_tool
# ==============================================================================
@tool
def financial_tool(
    avg_monthly_bill: float,
    system_capacity_kw: float,
    monthly_generation_kwh: float,
    tariff_per_kwh: float = DEFAULT_TARIFF_PER_KWH,
    cost_per_kw: float = DEFAULT_COST_PER_KW,
) -> Dict[str, Any]:
    """Calculate installation cost, PM Surya Ghar subsidy, bill savings, and payback.

    Args:
        avg_monthly_bill: Average monthly electricity bill in INR.
        system_capacity_kw: Recommended solar system capacity in kW.
        monthly_generation_kwh: Expected monthly electricity generation in kWh.
        tariff_per_kwh: Grid electricity tariff in INR/kWh (default ₹7.5).
        cost_per_kw: Gross benchmark turnkey cost per kW (default ₹55,000).

    Returns:
        Structured dictionary of financial metrics and payback period.
    """
    if system_capacity_kw <= 0:
        raise ValueError("System capacity must be greater than zero.")
    if avg_monthly_bill < 0:
        raise ValueError("Average monthly bill cannot be negative.")

    gross_cost_inr = round(system_capacity_kw * cost_per_kw, 2)
    subsidy_inr = calculate_pm_surya_ghar_subsidy(system_capacity_kw)
    net_investment_inr = round(max(0.0, gross_cost_inr - subsidy_inr), 2)

    # In Indian DISCOM billing (and net-metering regulations), domestic bills comprise:
    # 1. Variable energy charges (~75-80% of bill) which solar rooftop generation offsets.
    # 2. Mandatory fixed grid charges, sanctioned load fees, meter rent & duty (~20-25% of bill).
    # Even with 100% net generation, grid fixed charges remain payable (~₹150 to ₹650/month).
    fixed_charge_ratio = 0.245  # Standard residential fixed demand charges + cess ratio (~24.5%)
    grid_fixed_charges_inr = (
        round(max(150.0, avg_monthly_bill * fixed_charge_ratio), 2)
        if avg_monthly_bill > 0
        else 0.0
    )
    max_offsettable_bill = max(0.0, avg_monthly_bill - grid_fixed_charges_inr)

    # Monthly electricity generation value against variable energy charges
    potential_bill_reduction = monthly_generation_kwh * tariff_per_kwh
    monthly_savings_inr = round(min(potential_bill_reduction, max_offsettable_bill), 2)
    annual_savings_inr = round(monthly_savings_inr * 12.0, 2)
    post_solar_bill_inr = round(max(grid_fixed_charges_inr, avg_monthly_bill - monthly_savings_inr), 2)

    # Percentage bill reduction
    bill_reduction_pct = (
        round((monthly_savings_inr / avg_monthly_bill) * 100.0, 1)
        if avg_monthly_bill > 0
        else 0.0
    )

    # Simple payback period
    if annual_savings_inr > 0:
        payback_years = round(net_investment_inr / annual_savings_inr, 1)
    else:
        payback_years = None

    return {
        "cost_per_kw": cost_per_kw,
        "tariff_per_kwh": tariff_per_kwh,
        "gross_cost_inr": gross_cost_inr,
        "subsidy_inr": subsidy_inr,
        "net_investment_inr": net_investment_inr,
        "grid_fixed_charges_inr": grid_fixed_charges_inr,
        "monthly_savings_inr": monthly_savings_inr,
        "annual_savings_inr": annual_savings_inr,
        "post_solar_bill_inr": post_solar_bill_inr,
        "post_solar_monthly_bill_inr": post_solar_bill_inr,
        "bill_reduction_pct": bill_reduction_pct,
        "payback_years": payback_years,
    }


# ==============================================================================
# 7.4 Tool 3 — green_impact_tool
# ==============================================================================
@tool
def green_impact_tool(
    annual_generation_kwh: float,
    co2_factor: float = 0.82,
    coal_factor: float = 0.45,
    water_factor: float = 2.5,
    tree_absorption_kg: float = 22.0,
) -> Dict[str, Any]:
    """Calculate indicative environmental offsets from solar generation.

    Conversion benchmarks (CEA & Indian power grid averages):
    - CO₂ emissions avoided: 0.82 kg CO₂ / kWh
    - Coal displaced: 0.45 kg coal / kWh
    - Thermal power cooling water saved: 2.5 litres / kWh
    - Mature tree equivalent: 22.0 kg CO₂ absorbed per year per tree

    Returns:
        Structured dictionary of environmental impact metrics.
    """
    if annual_generation_kwh < 0:
        raise ValueError("Annual generation cannot be negative.")

    co2_avoided_kg = round(annual_generation_kwh * co2_factor, 2)
    coal_saved_kg = round(annual_generation_kwh * coal_factor, 2)
    water_saved_litres = round(annual_generation_kwh * water_factor, 2)
    trees_equivalent = int(co2_avoided_kg / tree_absorption_kg)

    return {
        "co2_avoided_kg": co2_avoided_kg,
        "coal_saved_kg": coal_saved_kg,
        "water_saved_litres": water_saved_litres,
        "trees_equivalent": trees_equivalent,
        "co2_factor_kg_per_kwh": co2_factor,
        "coal_factor_kg_per_kwh": coal_factor,
        "water_factor_litres_per_kwh": water_factor,
    }


# ==============================================================================
# 7.5 Master Strands Agent & Deterministic Pipeline
# ==============================================================================
# Instantiate the Strands Agent with the three tools.
# Does not invoke remote LLM or require AWS credentials.
try:
    solar_saathi_agent = Agent(
        tools=[solar_potential_tool, financial_tool, green_impact_tool],
        system_prompt=(
            "You are SolarSaathi, coordinating solar potential, financial savings, "
            "and environmental impact estimates for Indian households."
        ),
    )
except Exception as agent_err:
    logger.warning("Strands Agent initialized with fallback handler: %s", agent_err)
    solar_saathi_agent = None  # Core application continues deterministically


def generate_long_term_projections(
    net_investment_inr: float,
    annual_savings_inr: float,
    years: int = 10,
) -> Dict[str, Any]:
    """Generate year-by-year cumulative savings and net benefit curve."""
    labels: List[str] = []
    cumulative_savings_list: List[float] = []
    cumulative_net_benefit_list: List[float] = []

    for yr in range(1, years + 1):
        labels.append(f"Year {yr}")
        cum_savings = round(annual_savings_inr * yr, 2)
        cum_net_benefit = round(cum_savings - net_investment_inr, 2)
        cumulative_savings_list.append(cum_savings)
        cumulative_net_benefit_list.append(cum_net_benefit)

    # Determine break-even point
    break_even_reached = False
    break_even_year: Optional[float] = None
    if annual_savings_inr > 0:
        exact_payback = net_investment_inr / annual_savings_inr
        if 0 < exact_payback <= float(years):
            break_even_reached = True
            break_even_year = round(exact_payback, 1)

    return {
        "labels": labels,
        "cumulative_savings": cumulative_savings_list,
        "cumulative_net_benefit": cumulative_net_benefit_list,
        "initial_net_investment": net_investment_inr,
        "annual_savings": annual_savings_inr,
        "ten_year_net_benefit": cumulative_net_benefit_list[-1] if cumulative_net_benefit_list else 0.0,
        "break_even_reached": break_even_reached,
        "break_even_year": break_even_year,
    }


def run_solar_pipeline(
    bill1: float,
    bill2: float,
    bill3: float,
    roof_sqft: float,
    city: str,
    state: str = "",
) -> Dict[str, Any]:
    """Deterministic calculation pipeline executing the three tools and packaging the response.

    Does not make remote LLM calls or rely on cloud credentials.
    """
    # 1. Validation & Average Bill
    b1 = float(bill1)
    b2 = float(bill2)
    b3 = float(bill3)
    roof = float(roof_sqft)

    if min(b1, b2, b3) < 0:
        raise ValueError("Electricity bill values cannot be negative.")
    if roof <= 0:
        raise ValueError("Usable rooftop area must be greater than zero.")

    avg_monthly_bill = round((b1 + b2 + b3) / 3.0, 2)

    # 2. Tool 1: Solar Potential
    potential_data = solar_potential_tool(
        city=city,
        usable_roof_sqft=roof,
        state=state,
        avg_monthly_bill=avg_monthly_bill,
    )

    recommended_kw = potential_data["recommended_capacity_kw"]
    monthly_gen_kwh = potential_data["monthly_generation_kwh"]
    annual_gen_kwh = potential_data["annual_generation_kwh"]

    # 3. Tool 2: Financial & Subsidy
    financial_data = financial_tool(
        avg_monthly_bill=avg_monthly_bill,
        system_capacity_kw=recommended_kw,
        monthly_generation_kwh=monthly_gen_kwh,
    )

    # 4. Tool 3: Green Impact
    green_data = green_impact_tool(annual_generation_kwh=annual_gen_kwh)

    # 5. Long-term ROI projections (10-Year and 25-Year)
    roi_10yr = generate_long_term_projections(
        net_investment_inr=financial_data["net_investment_inr"],
        annual_savings_inr=financial_data["annual_savings_inr"],
        years=10,
    )

    roi_25yr = generate_long_term_projections(
        net_investment_inr=financial_data["net_investment_inr"],
        annual_savings_inr=financial_data["annual_savings_inr"],
        years=25,
    )

    # 6. Combined Structured Payload
    result: Dict[str, Any] = {
        "inputs": {
            "bill1": b1,
            "bill2": b2,
            "bill3": b3,
            "avg_monthly_bill": avg_monthly_bill,
            "roof_sqft": roof,
            "city": potential_data["city"],
            "state": potential_data["state"],
        },
        "potential": potential_data,
        "financial": financial_data,
        "environmental": green_data,
        "projections": {
            "ten_year": roi_10yr,
            "twenty_five_year": roi_25yr,
        },
        "charts": {
            "bill_comparison": {
                "current_monthly_bill": avg_monthly_bill,
                "post_solar_monthly_bill": financial_data["post_solar_monthly_bill_inr"],
                "monthly_savings": financial_data["monthly_savings_inr"],
                "bill_reduction_pct": financial_data["bill_reduction_pct"],
            },
            "roi_10yr": roi_10yr,
        },
        "assumptions": {
            "performance_ratio": DEFAULT_PERFORMANCE_RATIO,
            "cost_per_kw_inr": DEFAULT_COST_PER_KW,
            "tariff_per_kwh_inr": DEFAULT_TARIFF_PER_KWH,
            "regional_peak_sun_hours": potential_data["peak_sun_hours"],
            "subsidy_scheme": "PM Surya Ghar: Muft Bijli Yojana (Central Assistance)",
            "max_subsidy_cap_inr": 78000.0,
            "co2_factor_kg_per_kwh": 0.82,
            "coal_factor_kg_per_kwh": 0.45,
            "water_factor_litres_per_kwh": 2.5,
            "tree_factor_kg_co2_per_year": 22.0,
        },
        "live_weather_note": potential_data["live_weather_note"],
    }

    return result
