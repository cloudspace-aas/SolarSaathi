# SolarSaathi ☀️
### AI-Powered Rooftop Solar Savings Calculator & Environmental Impact Evaluator

SolarSaathi is a full-stack, local-first web application developed for Indian college environmental hackathons and educational demonstrations. It enables Indian households to evaluate their rooftop solar potential, calculate indicative central financial subsidies under the **PM Surya Ghar: Muft Bijli Yojana**, estimate net investments and simple payback periods, visualize 10-year cumulative returns, and quantify environmental benefits.

The application runs **100% locally** without requiring paid APIs, cloud services, AWS accounts, or remote LLM credentials.

---

## 🌟 Key Features

1. **Deterministic Multi-Tool AI Pipeline**: Built using the AWS Strands Agents SDK (`strands-agents`) with three modular `@tool` functions (`solar_potential_tool`, `financial_tool`, `green_impact_tool`).
2. **All 36 Indian States & Union Territories**: Calibrated using fixed regional solar-insolation planning benchmarks (ranging from 4.1 to 5.8 peak sun hours per day).
3. **PM Surya Ghar Subsidy Engine**: Tiered prorated calculation of Central Financial Assistance up to the residential cap of ₹78,000.
4. **Visual Analytics**: Interactive Chart.js graphs displaying:
   - Monthly electricity bill comparison (Before vs. After Solar).
   - 10-year cumulative return on investment (ROI) with break-even indicators.
5. **Local Persistent Storage**: SQLite database storing calculation history with parameterized queries.
6. **Optional Real-Time Climate Observation**: Optional Open-Meteo geocoding and live direct solar irradiance lookup with graceful offline sensor fallback.
7. **Offline-First Architecture**: Vendored local Chart.js asset, deterministic Python logic, and local SQLite ensure complete functionality even without internet connectivity.
8. **Responsive Indian Climate-Tech Design**: Forest green (`#1B4332`), Sage green (`#40916C`), Warm sand (`#DDB892`), and Soft cream (`#F8F6F0`) visual design with mobile menu support and keyboard accessibility.

---

## 🏗️ Project Architecture & File Structure

```text
envhacks/
├── app.py                  # Flask backend server, REST API endpoints, input validation & CORS
├── solar_agent.py          # Strands Agents SDK tools & deterministic calculation pipeline
├── database.py             # SQLite connection management, schema initialization, and queries
├── requirements.txt        # Python dependency manifest
├── README.md               # Project documentation & reference manual
├── .gitignore              # Git ignore rules for virtual environments, caches, and DB files
├── solarsaathi.db          # Auto-generated local SQLite database
└── static/
    ├── index.html          # Semantic HTML5 single-page application
    ├── style.css           # Custom CSS3 styling and responsive design system
    ├── script.js           # Vanilla ES6 client logic, Chart.js integrations & DOM updates
    └── chart.min.js        # Vendored offline Chart.js library
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.9+ (Python 3.10–3.14 supported)
- Standard browser (Chrome, Firefox, Safari, Edge)

### 2. Environment Setup & Dependency Installation

Clone or open the project directory:
```bash
cd ~/envhacks
```

Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

Install required packages:
```bash
pip install -r requirements.txt
```

### 3. Run the Application

Start the Flask server:
```bash
python app.py
```

The application will start at:
👉 **`http://localhost:5000`**

Open this URL in your web browser.

---

## 🧮 Mathematical Formulas & Benchmark Assumptions

### 1. Solar Potential & Generation (`solar_potential_tool`)
- **Physical Rooftop Capacity**:
  $$\text{Raw Roof Capacity (kW)} = \frac{\text{Usable Rooftop Area (sq. ft)}}{100}$$
- **Demand Calibration**:
  $$\text{Monthly Units Needed} = \frac{\text{Average Monthly Bill (₹)}}{7.5\text{ ₹/kWh}}$$
  $$\text{Daily Units Needed} = \frac{\text{Monthly Units}}{30}$$
  $$\text{Target Capacity (kW)} = \frac{\text{Daily Units Needed}}{\text{Peak Sun Hours} \times 0.80} \times 1.10$$
  $$\text{Recommended Capacity (kW)} = \min(\text{Raw Roof Capacity}, \max(1.0, \text{Target Capacity}))$$
- **Monthly Generation**:
  $$\text{Monthly Generation (kWh)} = \text{Capacity (kW)} \times \text{Peak Sun Hours} \times 30 \times 0.80$$
- **Annual Generation**:
  $$\text{Annual Generation (kWh)} = \text{Monthly Generation} \times 12$$

### 2. Financial Economics & Subsidy (`financial_tool`)
- **Gross Turnkey Cost**:
  $$\text{Gross Cost (₹)} = \text{Capacity (kW)} \times 55,000\text{ ₹/kW}$$
- **PM Surya Ghar Subsidy (Tiered Central Assistance)**:
  - First 1 kW: ₹30,000 per kW (prorated)
  - Next 1 kW (1 to 2 kW): ₹30,000 per kW (prorated)
  - Next 1 kW (2 to 3 kW): ₹18,000 per kW (prorated)
  - Above 3 kW: ₹0 additional central assistance
  - Residential ceiling: **₹78,000**
- **Net Investment**:
  $$\text{Net Investment (₹)} = \max(0, \text{Gross Cost} - \text{Subsidy})$$
- **Monthly Bill Savings**:
  $$\text{Potential Monthly Value} = \text{Monthly Generation (kWh)} \times 7.5\text{ ₹/kWh}$$
  $$\text{Monthly Savings (₹)} = \min(\text{Potential Monthly Value}, \text{Average Monthly Bill})$$
  $$\text{Post-Solar Bill (₹)} = \max(0, \text{Average Monthly Bill} - \text{Monthly Savings})$$
- **Simple Payback Period**:
  $$\text{Payback (Years)} = \frac{\text{Net Investment (₹)}}{\text{Annual Savings (₹)}}$$

### 3. Environmental Impact Conversions (`green_impact_tool`)
Conversion baselines derived from Central Electricity Authority (CEA) average grid displacement:
- **CO₂ Emissions Avoided**: $0.82\text{ kg CO}_2 / \text{kWh}$
- **Thermal Coal Displaced**: $0.45\text{ kg Coal} / \text{kWh}$
- **Power Cooling Water Conserved**: $2.5\text{ Litres} / \text{kWh}$
- **Equivalent Mature Trees**: $1\text{ Tree} \approx 22.0\text{ kg CO}_2\text{ absorbed per year}$

---

## 🤖 AWS Strands Agents SDK Integration

SolarSaathi integrates the **AWS Strands Agents SDK** (`strands-agents`) via modular tools:

```python
from strands import Agent, tool

@tool
def solar_potential_tool(city: str, usable_roof_sqft: float, state: str = "", ...) -> dict:
    ...

@tool
def financial_tool(avg_monthly_bill: float, system_capacity_kw: float, ...) -> dict:
    ...

@tool
def green_impact_tool(annual_generation_kwh: float) -> dict:
    ...

solar_saathi_agent = Agent(
    tools=[solar_potential_tool, financial_tool, green_impact_tool],
    system_prompt="You are SolarSaathi, coordinating solar potential, financial savings, and environmental impact estimates for Indian households."
)
```

### Why Core Calculations Require No Hosted Credentials
Strands tools are pure Python functions wrapped with the `@tool` decorator. In SolarSaathi:
1. All mathematical, financial, and environmental operations are computed deterministically via `run_solar_pipeline(...)`.
2. No remote LLM or Amazon Bedrock invocation is required for calculations.
3. The application avoids hallucinations, arithmetic errors, API fees, rate limits, and network latency.
4. If a local model provider is connected in the future, the agent is already registered and ready to execute conversational queries over these tools.

---

## 🔌 API Endpoints Reference

### 1. `GET /api/health`
Checks the server and local SQLite database connection.

**Response (200 OK):**
```json
{
  "app": "SolarSaathi",
  "database": "connected",
  "status": "ok",
  "version": "1.0.0"
}
```

### 2. `POST /api/calculate`
Calculates solar potential, financial returns, and environmental impact, saving the record to SQLite.

**Request Body:**
```json
{
  "bill1": 2500,
  "bill2": 2800,
  "bill3": 2650,
  "roof_sqft": 500,
  "city": "Jaipur",
  "state": "Rajasthan"
}
```

**Response (200 OK):**
```json
{
  "estimate_id": 1,
  "inputs": {
    "bill1": 2500.0,
    "bill2": 2800.0,
    "bill3": 2650.0,
    "avg_monthly_bill": 2650.0,
    "roof_sqft": 500.0,
    "city": "Jaipur",
    "state": "Rajasthan"
  },
  "potential": {
    "recommended_capacity_kw": 2.9,
    "raw_roof_capacity_kw": 5.0,
    "peak_sun_hours": 5.6,
    "monthly_generation_kwh": 389.76,
    "annual_generation_kwh": 4677.12,
    "live_weather_note": "Live Weather: Sensor offline (using regional insolation benchmark)."
  },
  "financial": {
    "gross_cost_inr": 159500.0,
    "subsidy_inr": 76200.0,
    "net_investment_inr": 83300.0,
    "monthly_savings_inr": 2650.0,
    "annual_savings_inr": 31800.0,
    "post_solar_bill_inr": 0.0,
    "bill_reduction_pct": 100.0,
    "payback_years": 2.6
  },
  "environmental": {
    "co2_avoided_kg": 3835.24,
    "coal_saved_kg": 2104.7,
    "water_saved_litres": 11692.8,
    "trees_equivalent": 174
  },
  "charts": {
    "bill_comparison": { ... },
    "roi_10yr": {
      "labels": ["Year 1", ..., "Year 10"],
      "cumulative_net_benefit": [-51500.0, -19700.0, 12100.0, ...],
      "break_even_reached": true,
      "break_even_year": 2.6,
      "ten_year_net_benefit": 234700.0
    }
  }
}
```

### 3. `GET /api/estimates?limit=5`
Retrieves the 5 most recent calculations from the local database.

---

## 🔒 Security & Reliability Measures

- **Strict Server Validation**: Rejects non-numeric, negative, NaN, infinite, or absurd inputs (> ₹5,00,000 bills, > 1,00,000 sq.ft roof).
- **Parameterized SQL**: All database operations use SQLite parameter binding (`:city`, `:state`, etc.) to prevent SQL injection.
- **Controlled CORS**: Restricted to `http://localhost:5000` and `http://127.0.0.1:5000`.
- **Safe Network Timeouts**: Open-Meteo requests have a strict 2.5s timeout and gracefully degrade to regional benchmarks if disconnected.
- **Payload Limits**: Max body size capped at 1 MB to prevent memory exhaustion.
- **XSS Prevention**: User inputs rendered into the history table are sanitized via HTML entity escaping.

---

## ⚖️ Disclaimers

1. **Financial Disclaimer**: All financial estimates (turnkey costs, subsidies, bill reductions, payback) are indicative educational calculations based on benchmark assumptions. Actual costs, DISCOM net-metering approvals, feed-in tariffs, and subsidy disbursements depend on state regulations and vendor quotes.
2. **Data & Environmental Disclaimer**: Environmental metrics represent simplified grid-average illustrative factors from Central Electricity Authority (CEA) baselines, not direct site measurements. This application does not replace an on-site structural engineering survey or shadow analysis.

---

## 📜 Official Resources
- **National Portal for PM Surya Ghar: Muft Bijli Yojana**: [https://www.myscheme.gov.in/schemes/pmsgmb](https://www.myscheme.gov.in/schemes/pmsgmb)
