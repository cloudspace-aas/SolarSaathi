/**
 * SolarSaathi ☀️ — Client-side Application Logic
 * Handles interactive calculator, real-time validations, Chart.js visualizations,
 * SQLite history loading, mobile navigation, and accessible accordion behaviors.
 */

// ==============================================================================
// 1. Centralized Illustrative Sample Baseline Data
// ==============================================================================
const SAMPLE_ESTIMATE = {
  inputs: {
    bill1: 2500,
    bill2: 2800,
    bill3: 2650,
    avg_monthly_bill: 2650,
    roof_sqft: 500,
    city: "Jaipur",
    state: "Rajasthan",
  },
  potential: {
    recommended_capacity_kw: 2.3,
    peak_sun_hours: 5.6,
    monthly_generation_kwh: 309.1,
    annual_generation_kwh: 3709.4,
  },
  financial: {
    gross_cost_inr: 126500,
    subsidy_inr: 65400,
    net_investment_inr: 61100,
    grid_fixed_charges_inr: 650,
    monthly_savings_inr: 2000,
    post_solar_bill_inr: 650,
    annual_savings_inr: 24000,
    bill_reduction_pct: 75.5,
    payback_years: 2.5,
  },
  environmental: {
    co2_avoided_kg: 3041.7,
    coal_saved_kg: 1669.2,
    water_saved_litres: 9273.5,
    trees_equivalent: 138,
  },
  projections: {
    ten_year: {
      labels: ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6", "Year 7", "Year 8", "Year 9", "Year 10"],
      cumulative_savings: [24000, 48000, 72000, 96000, 120000, 144000, 168000, 192000, 216000, 240000],
      cumulative_net_benefit: [-37100, -13100, 10900, 34900, 58900, 82900, 106900, 130900, 154900, 178900],
      initial_net_investment: 61100,
      annual_savings: 24000,
      ten_year_net_benefit: 178900,
      break_even_reached: true,
      break_even_year: 2.5,
    }
  },
  live_weather_note: "Live Weather: Sensor offline (using regional insolation benchmark).",
};

// Global chart references for safe re-rendering
let billChartInstance = null;
let roiChartInstance = null;

// ==============================================================================
// 2. Formatters
// ==============================================================================
const inrFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const numFormatter = new Intl.NumberFormat('en-IN', {
  maximumFractionDigits: 1,
});

function formatINR(val) {
  if (val === null || val === undefined || isNaN(val)) return '₹0';
  return inrFormatter.format(val);
}

function formatNum(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(val)) return '0';
  return Number(val).toLocaleString('en-IN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  });
}

function formatDate(isoStr) {
  if (!isoStr) return 'Recent';
  try {
    const d = new Date(isoStr.replace(' ', 'T') + 'Z');
    if (isNaN(d.getTime())) return isoStr;
    return d.toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  } catch (e) {
    return isoStr;
  }
}

// ==============================================================================
// 3. UI Dashboard Updaters
// ==============================================================================
function updateDashboardUI(data, isUserEstimate = false) {
  // 1. Live Climate Alert Banner
  const weatherText = document.getElementById('weatherStatusText');
  if (weatherText) {
    const note = data.live_weather_note || "Live Weather: Sensor offline (using regional insolation benchmark).";
    weatherText.textContent = `${note} | Financial estimates use regional solar-insolation benchmarks.`;
  }

  // 2. Badges & Location
  const statusBadge = document.getElementById('estimateStatusBadge');
  const locBadge = document.getElementById('estimateLocationBadge');
  const timeBadge = document.getElementById('estimateTimestamp');

  if (statusBadge) {
    if (isUserEstimate) {
      statusBadge.textContent = "Your Estimate";
      statusBadge.className = "status-pill badge-sage";
    } else {
      statusBadge.textContent = "Sample Estimate";
      statusBadge.className = "status-pill badge-plum";
    }
  }

  if (locBadge) {
    const city = data.inputs.city || "Representative City";
    const state = data.inputs.state || "India";
    const sunHours = data.potential.peak_sun_hours ? `${data.potential.peak_sun_hours} Peak Sun Hours` : "4.8 Sun Hours";
    locBadge.textContent = `${city}, ${state} (${sunHours})`;
  }

  if (timeBadge) {
    timeBadge.textContent = isUserEstimate ? `Calculated ${new Date().toLocaleTimeString('en-IN')}` : "Illustrative baseline";
  }

  // 3. Key Financial Metrics
  const recKw = document.getElementById('valRecommendedKw');
  const monthlyGen = document.getElementById('valMonthlyGenKwh');
  const annualGen = document.getElementById('valAnnualGenKwh');
  const subsidy = document.getElementById('valSubsidyInr');
  const grossCost = document.getElementById('valGrossCostInr');
  const netInv = document.getElementById('valNetInvestmentInr');
  const monthlySav = document.getElementById('valMonthlySavingsInr');
  const payback = document.getElementById('valPaybackYears');
  const annualSav = document.getElementById('valAnnualSavingsInr');
  const postBill = document.getElementById('valPostSolarBillInr');

  if (recKw) recKw.textContent = formatNum(data.potential.recommended_capacity_kw, 1);
  if (monthlyGen) monthlyGen.textContent = `${formatNum(data.potential.monthly_generation_kwh, 0)} kWh`;
  if (annualGen) annualGen.textContent = `${formatNum(data.potential.annual_generation_kwh, 0)} kWh`;
  if (subsidy) subsidy.textContent = formatINR(data.financial.subsidy_inr);
  if (grossCost) grossCost.textContent = formatINR(data.financial.gross_cost_inr);
  if (netInv) netInv.textContent = formatINR(data.financial.net_investment_inr);
  if (monthlySav) monthlySav.textContent = formatINR(data.financial.monthly_savings_inr);
  if (annualSav) annualSav.textContent = formatINR(data.financial.annual_savings_inr);
  if (postBill) postBill.textContent = `${formatINR(data.financial.post_solar_bill_inr)} / mo`;

  if (payback) {
    if (data.financial.payback_years !== null && data.financial.payback_years !== undefined) {
      payback.textContent = `${data.financial.payback_years}`;
    } else {
      payback.textContent = "N/A";
    }
  }

  // 4. Environmental Impact
  const co2 = document.getElementById('valCo2Avoided');
  const coal = document.getElementById('valCoalSaved');
  const water = document.getElementById('valWaterSaved');
  const trees = document.getElementById('valTreesEquivalent');

  if (co2) co2.textContent = formatNum(data.environmental.co2_avoided_kg, 0);
  if (coal) coal.textContent = formatNum(data.environmental.coal_saved_kg, 0);
  if (water) water.textContent = formatNum(data.environmental.water_saved_litres, 0);
  if (trees) trees.textContent = formatNum(data.environmental.trees_equivalent, 0);

  // 5. Chart Metadata and Badges
  const monthlyPill = document.getElementById('monthlySavingsPill');
  if (monthlyPill) {
    const cut = data.financial.bill_reduction_pct || 0;
    monthlyPill.textContent = `Saves ${formatINR(data.financial.monthly_savings_inr)} / mo (${cut}% cut)`;
  }

  const chartAvgLbl = document.getElementById('chartAvgBillLabel');
  const chartPostLbl = document.getElementById('chartPostBillLabel');
  const chartSavLbl = document.getElementById('chartMonthlySavingsLabel');

  if (chartAvgLbl) chartAvgLbl.textContent = formatINR(data.inputs.avg_monthly_bill);
  if (chartPostLbl) chartPostLbl.textContent = formatINR(data.financial.post_solar_bill_inr);
  if (chartSavLbl) chartSavLbl.textContent = formatINR(data.financial.monthly_savings_inr);

  const breakEvenPill = document.getElementById('breakEvenPill');
  const roi10 = data.projections?.ten_year || SAMPLE_ESTIMATE.projections.ten_year;
  if (breakEvenPill) {
    if (roi10.break_even_reached && roi10.break_even_year) {
      breakEvenPill.textContent = `Break-even: ~${roi10.break_even_year} Years`;
    } else {
      breakEvenPill.textContent = `Break-even > 10 Years`;
    }
  }

  // ROI Summary Grid Items
  const roiNet = document.getElementById('roiNetInv');
  const roiAnn = document.getElementById('roiAnnualSav');
  const roiPb = document.getElementById('roiPayback');
  const roiTen = document.getElementById('roiTenYear');

  if (roiNet) roiNet.textContent = formatINR(data.financial.net_investment_inr);
  if (roiAnn) roiAnn.textContent = formatINR(data.financial.annual_savings_inr);
  if (roiPb) roiPb.textContent = data.financial.payback_years ? `${data.financial.payback_years} Yrs` : "N/A";
  if (roiTen) roiTen.textContent = formatINR(roi10.ten_year_net_benefit);

  // 6. Update Visual Charts
  renderCharts(data);
}

// ==============================================================================
// 4. Chart.js Visualizations (Editorial Plum & Sage Palette)
// ==============================================================================
function renderCharts(data) {
  if (typeof Chart === 'undefined') {
    console.warn("Chart.js not loaded. Visual graphs unavailable.");
    const wraps = document.querySelectorAll('.chart-canvas-wrap');
    wraps.forEach(wrap => {
      wrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#624765;font-size:0.9rem;">Interactive chart library loading or offline. Metrics displayed above.</div>`;
    });
    return;
  }

  // Chart 1: Grouped Bar Chart (Current vs Post-Solar Monthly & Annual Bill)
  const barCanvas = document.getElementById('billComparisonChart');
  if (barCanvas) {
    if (billChartInstance) {
      billChartInstance.destroy();
    }

    const currentMonthly = Number(data.inputs.avg_monthly_bill) || 0;
    const postMonthly = Number(data.financial.post_solar_bill_inr) || 0;
    const monthlySavings = Number(data.financial.monthly_savings_inr) || 0;
    const cutPct = Number(data.financial.bill_reduction_pct) || 0;

    const currentAnnual = currentMonthly * 12;
    const postAnnual = postMonthly * 12;
    const annualSavings = monthlySavings * 12;

    billChartInstance = new Chart(barCanvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: ['Monthly Bill (₹)', 'Annual Bill (₹)'],
        datasets: [
          {
            label: 'Current Bill (Without Solar)',
            data: [currentMonthly, currentAnnual],
            backgroundColor: '#302238',  // Deep Plum
            borderColor: '#24192B',
            borderWidth: 1,
            borderRadius: 4,
            barPercentage: 0.65,
            categoryPercentage: 0.6,
          },
          {
            label: 'Post-Solar Bill (With Solar)',
            data: [postMonthly, postAnnual],
            backgroundColor: '#527C69',  // Moss Sage
            borderColor: '#436656',
            borderWidth: 1,
            borderRadius: 4,
            barPercentage: 0.65,
            categoryPercentage: 0.6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              boxWidth: 12,
              boxHeight: 12,
              borderRadius: 2,
              useBorderRadius: true,
              font: { family: 'Manrope', size: 12, weight: 600 },
              color: '#302238',
              padding: 16,
            },
          },
          tooltip: {
            backgroundColor: '#302238',
            borderColor: '#624765',
            borderWidth: 1,
            titleFont: { family: 'Manrope', size: 12, weight: 700 },
            bodyFont: { family: 'Manrope', size: 12 },
            padding: 12,
            cornerRadius: 6,
            callbacks: {
              label: function(context) {
                const val = Number(context.raw);
                const isMonthly = context.dataIndex === 0;
                const isPostSolar = context.datasetIndex === 1;

                if (isPostSolar) {
                  const sav = isMonthly ? monthlySavings : annualSavings;
                  const unit = isMonthly ? '/mo' : '/yr';
                  return `Post-Solar: ₹${val.toLocaleString('en-IN')} (Saves ₹${sav.toLocaleString('en-IN')} ${unit} • ${cutPct}% cut)`;
                } else {
                  const unit = isMonthly ? '/mo' : '/yr';
                  return `Current: ₹${val.toLocaleString('en-IN')} ${unit}`;
                }
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return '₹' + Number(value).toLocaleString('en-IN');
              },
              color: '#624765',
              font: { family: 'Manrope', size: 11 },
            },
            grid: { color: '#E3DDD5' },
          },
          x: {
            ticks: {
              color: '#302238',
              font: { family: 'Manrope', size: 12, weight: 600 },
            },
            grid: { display: false },
          },
        },
      },
    });
  }

  // Chart 2: Ten-Year ROI Line Chart
  const roiCanvas = document.getElementById('roiChart');
  if (roiCanvas) {
    if (roiChartInstance) {
      roiChartInstance.destroy();
    }

    const roi10 = data.projections?.ten_year || SAMPLE_ESTIMATE.projections.ten_year;
    const labels = roi10.labels || ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6", "Year 7", "Year 8", "Year 9", "Year 10"];
    const netBenefits = roi10.cumulative_net_benefit || [];

    roiChartInstance = new Chart(roiCanvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Net Cumulative Benefit (₹)',
          data: netBenefits,
          borderColor: '#527C69',       // Moss Sage
          backgroundColor: 'rgba(82, 124, 105, 0.10)',
          fill: true,
          tension: 0.2,
          borderWidth: 2,
          pointBackgroundColor: '#302238', // Deep Plum
          pointBorderColor: '#FFFFFF',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#302238',
            borderColor: '#624765',
            borderWidth: 1,
            titleFont: { family: 'Manrope', size: 12, weight: 700 },
            bodyFont: { family: 'Manrope', size: 12 },
            padding: 12,
            cornerRadius: 6,
            callbacks: {
              label: function(context) {
                const val = Number(context.raw);
                const prefix = val >= 0 ? '+₹' : '-₹';
                return `Net Benefit: ${prefix}${Math.abs(val).toLocaleString('en-IN')}`;
              }
            }
          }
        },
        scales: {
          y: {
            ticks: {
              callback: function(value) {
                const v = Number(value);
                const prefix = v >= 0 ? '₹' : '-₹';
                return prefix + Math.abs(v).toLocaleString('en-IN');
              },
              color: '#624765',
              font: { family: 'Manrope', size: 11 }
            },
            grid: {
              color: function(context) {
                if (context.tick.value === 0) {
                  return '#302238'; // Zero baseline
                }
                return '#E3DDD5';
              },
              lineWidth: function(context) {
                return context.tick.value === 0 ? 1.5 : 1;
              }
            }
          },
          x: {
            ticks: {
              color: '#624765',
              font: { family: 'Manrope', size: 11 }
            },
            grid: { display: false }
          }
        }
      }
    });
  }
}

// ==============================================================================
// 5. Recent History Table Loader
// ==============================================================================
async function loadRecentEstimates() {
  const tbody = document.getElementById('historyTableBody');
  if (!tbody) return;

  try {
    const resp = await fetch('/api/estimates?limit=5');
    if (!resp.ok) throw new Error("Could not fetch estimates.");

    const records = await resp.json();

    if (!Array.isArray(records) || records.length === 0) {
      tbody.innerHTML = `
        <tr class="empty-row">
          <td colspan="7">No saved calculations yet. Use the calculator above to run your first assessment!</td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = records.map(rec => {
      const formattedDate = formatDate(rec.created_at);
      const loc = `${escapeHtml(rec.city)}, ${escapeHtml(rec.state)}`;
      const avgBill = formatINR(rec.avg_bill);
      const kw = `${formatNum(rec.recommended_kw, 1)} kW`;
      const subsidy = formatINR(rec.subsidy_inr);
      const net = formatINR(rec.net_investment_inr);
      const payback = rec.payback_years ? `${rec.payback_years} Yrs` : 'N/A';

      return `
        <tr>
          <td class="td-left">${formattedDate}</td>
          <td class="td-left"><strong>${loc}</strong></td>
          <td class="td-right">${avgBill}</td>
          <td class="td-right">${kw}</td>
          <td class="td-right text-sage"><strong>${subsidy}</strong></td>
          <td class="td-right">${net}</td>
          <td class="td-right"><strong>${payback}</strong></td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    console.warn("History fetch notice:", err);
    tbody.innerHTML = `
      <tr class="empty-row">
        <td colspan="7">Unable to load local history from server. Ensure backend is running.</td>
      </tr>
    `;
  }
}

// Security: escape HTML in user-derived strings before rendering
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ==============================================================================
// 6. Form Submission & Inline Validations
// ==============================================================================
function setupCalculatorForm() {
  const form = document.getElementById('solarForm');
  const calculateBtn = document.getElementById('calculateBtn');
  const formAlert = document.getElementById('formAlert');

  if (!form || !calculateBtn) return;

  // Clear specific field error
  function clearErrors() {
    ['bill1', 'bill2', 'bill3', 'roof', 'state', 'city'].forEach(id => {
      const errEl = document.getElementById(`${id}-error`);
      if (errEl) errEl.textContent = '';
    });
    if (formAlert) {
      formAlert.textContent = '';
      formAlert.classList.add('hidden');
    }
  }

  form.addEventListener('submit', async function(e) {
    e.preventDefault();
    clearErrors();

    // Field references
    const b1Input = document.getElementById('bill1');
    const b2Input = document.getElementById('bill2');
    const b3Input = document.getElementById('bill3');
    const roofInput = document.getElementById('roof_sqft');
    const stateInput = document.getElementById('state');
    const cityInput = document.getElementById('city');

    let hasError = false;

    // Validation 1: Bills
    const b1Val = parseFloat(b1Input.value);
    const b2Val = parseFloat(b2Input.value);
    const b3Val = parseFloat(b3Input.value);

    if (isNaN(b1Val) || b1Val < 0) {
      document.getElementById('bill1-error').textContent = 'Enter a valid non-negative bill (₹).';
      hasError = true;
    }
    if (isNaN(b2Val) || b2Val < 0) {
      document.getElementById('bill2-error').textContent = 'Enter a valid non-negative bill (₹).';
      hasError = true;
    }
    if (isNaN(b3Val) || b3Val < 0) {
      document.getElementById('bill3-error').textContent = 'Enter a valid non-negative bill (₹).';
      hasError = true;
    }

    // Validation 2: Rooftop Area
    const roofVal = parseFloat(roofInput.value);
    if (isNaN(roofVal) || roofVal < 10) {
      document.getElementById('roof-error').textContent = 'Usable rooftop area must be at least 10 sq. ft.';
      hasError = true;
    } else if (roofVal > 100000) {
      document.getElementById('roof-error').textContent = 'Rooftop area exceeds reasonable residential limit.';
      hasError = true;
    }

    // Validation 3: State Selection
    const stateVal = stateInput.value.trim();
    if (!stateVal) {
      document.getElementById('state-error').textContent = 'Please select your Indian State or Union Territory.';
      hasError = true;
    }

    if (hasError) {
      if (formAlert) {
        formAlert.textContent = 'Please correct the highlighted fields above.';
        formAlert.classList.remove('hidden');
      }
      return;
    }

    // Prepare JSON payload
    const payload = {
      bill1: b1Val,
      bill2: b2Val,
      bill3: b3Val,
      roof_sqft: roofVal,
      state: stateVal,
      city: cityInput.value.trim(),
    };

    // Button loading state
    const btnText = calculateBtn.querySelector('.btn-text');
    const btnSpinner = calculateBtn.querySelector('.btn-spinner');
    calculateBtn.disabled = true;
    if (btnText) btnText.textContent = 'Evaluating Solar Potential...';
    if (btnSpinner) btnSpinner.classList.remove('hidden');

    try {
      const response = await fetch('/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || `Server error (${response.status})`);
      }

      // Update Dashboard with true calculation results
      updateDashboardUI(result, true);

      // Refresh Recent Calculations history table
      loadRecentEstimates();

      // Smooth scroll down to results section
      const resultsSection = document.getElementById('results');
      if (resultsSection) {
        resultsSection.scrollIntoView({ behavior: 'smooth' });
      }

    } catch (err) {
      console.error("Calculation request failed:", err);
      if (formAlert) {
        formAlert.textContent = err.message || 'An error occurred while evaluating solar savings. Please try again.';
        formAlert.classList.remove('hidden');
      }
    } finally {
      calculateBtn.disabled = false;
      if (btnText) btnText.textContent = 'Calculate Solar Potential & Savings →';
      if (btnSpinner) btnSpinner.classList.add('hidden');
    }
  });
}

// ==============================================================================
// 7. Accordion (FAQs)
// ==============================================================================
function setupFaqAccordion() {
  const accordion = document.getElementById('faqAccordion');
  if (!accordion) return;

  const headers = accordion.querySelectorAll('.accordion-header');

  headers.forEach(header => {
    header.addEventListener('click', () => {
      const isExpanded = header.getAttribute('aria-expanded') === 'true';
      const bodyId = header.getAttribute('aria-controls');
      const body = document.getElementById(bodyId);

      // Close other accordion items for clean single-item expansion
      headers.forEach(otherHeader => {
        if (otherHeader !== header) {
          otherHeader.setAttribute('aria-expanded', 'false');
          const otherBody = document.getElementById(otherHeader.getAttribute('aria-controls'));
          if (otherBody) otherBody.hidden = true;
        }
      });

      // Toggle current
      header.setAttribute('aria-expanded', String(!isExpanded));
      if (body) {
        body.hidden = isExpanded;
      }
    });

    // Keyboard support for Enter and Space
    header.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        header.click();
      }
    });
  });
}

// ==============================================================================
// 8. Mobile Navigation & Clean Smooth Scrolling (Without Hash or Title Changes)
// ==============================================================================
const SITE_TITLE = "SolarSaathi ☀️ | Rooftop Solar Savings & Environmental Impact Evaluator";

function setupCleanNavigation() {
  const navToggle = document.getElementById('navToggle');
  const navMenu = document.getElementById('navMenu');

  // 1. If page loaded with a hash in URL, strip it so the browser omnibox/search bar stays clean
  if (window.location.hash) {
    history.replaceState(null, '', window.location.pathname + window.location.search);
  }
  document.title = SITE_TITLE;

  // 2. Mobile hamburger menu toggle
  if (navToggle && navMenu) {
    navToggle.addEventListener('click', () => {
      const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';
      navToggle.setAttribute('aria-expanded', String(!isExpanded));
      navMenu.classList.toggle('active');
    });
  }

  // 3. Intercept all internal anchor clicks to prevent hash mutation in the search bar
  document.addEventListener('click', (e) => {
    const anchor = e.target.closest('a[href^="#"]');
    if (!anchor) return;

    const href = anchor.getAttribute('href');
    if (!href) return;

    // Prevent native browser hash jump which alters the search bar title
    e.preventDefault();

    // Close mobile nav if open
    if (navToggle && navMenu && navMenu.classList.contains('active')) {
      navToggle.setAttribute('aria-expanded', 'false');
      navMenu.classList.remove('active');
    }

    // Scroll smoothly to top or target section
    if (href === '#' || href === '#top') {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    } else {
      try {
        const targetElement = document.querySelector(href);
        if (targetElement) {
          targetElement.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      } catch (err) {
        console.warn('Navigation target element not found:', href);
      }
    }

    // Keep URL and browser omnibox search bar completely clean and unchanging
    if (window.location.hash) {
      history.replaceState(null, '', window.location.pathname + window.location.search);
    }
    document.title = SITE_TITLE;
  });

  // 4. Safeguard: if any hash change ever triggers, immediately strip it
  window.addEventListener('hashchange', () => {
    history.replaceState(null, '', window.location.pathname + window.location.search);
    document.title = SITE_TITLE;
  });
}

// ==============================================================================
// 9. Application Initialization
// ==============================================================================
document.addEventListener('DOMContentLoaded', () => {
  // 1. Render initial illustrative sample dashboard
  updateDashboardUI(SAMPLE_ESTIMATE, false);

  // 2. Set dynamic current year in footer
  const yearEl = document.getElementById('currentYear');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  // 3. Attach interactive form and UI handlers
  setupCalculatorForm();
  setupFaqAccordion();
  setupCleanNavigation();

  // 4. Load recent SQLite history
  loadRecentEstimates();

  // 5. Hook up refresh history button
  const refreshBtn = document.getElementById('refreshHistoryBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadRecentEstimates();
    });
  }
});

