// static/metrics/performance_metrics.js
// NOTE: this file is loaded as <script type="module" ...> so imports are OK.

import { bindToggleGroup } from "./toggles.js";
import { createHorizontalBar, createDonutZones } from "./charts.js";

const CYCLING_ZONE_COLORS = {
  1: "#4c6ef5",
  2: "#22c55e",
  3: "#f59e0b",
  4: "#ef4444",
  5: "#ec4899",
  6: "#a855f7",
  7: "#9333ea",
};

const RUNNING_ZONE_COLORS = {
  recovery: "#4c6ef5",
  easy: "#22c55e",
  moderate: "#fbbf24",
  challenging: "#f59e0b",
  hard: "#ef4444",
  very_hard: "#a855f7",
  max: "#ec4899",
};

function getData() {
  const el = document.getElementById("metrics-data");
  if (!el) return {};
  try {
    return JSON.parse(el.textContent || "{}");
  } catch {
    return {};
  }
}

function showMetricsContent() {
  document.getElementById("global-loader")?.classList.add("hidden");
  const skeleton = document.getElementById("metrics-skeleton");
  if (skeleton) skeleton.style.display = "none";
  document.getElementById("metrics-real-content")?.classList.remove("hidden");
  const content = document.getElementById("metrics-content");
  if (content) content.style.opacity = "1";
}

function setText(el, value, empty = "—") {
  if (!el) return;
  el.textContent = value && value > 0 ? value : empty;
}

function destroyChartSafe(chart) {
  if (chart && typeof chart.destroy === "function") {
    try {
      chart.destroy();
    } catch (_) {}
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const data = getData();

  // Always reveal even if something below fails
  try {
    // -------------------------
    // Achievements/Milestones
    // -------------------------
    bindToggleGroup({
      root: document,
      buttonSelector: ".metrics-tab-btn",
      activeClasses: ["bg-primary", "text-white"],
      inactiveClasses: ["bg-gray-100", "dark:bg-gray-700", "text-gray-700", "dark:text-gray-300"],
      getValue: (btn) => btn.dataset.tab,
      onChange: (tab) => {
        document.getElementById("achievements-tab")?.classList.toggle("hidden", tab !== "achievements");
        document.getElementById("milestones-tab")?.classList.toggle("hidden", tab !== "milestones");
      },
    });

    // -------------------------
    // Personal Records + Power Curve
    // Requires these elements in your PR partial:
    // - .pr-period-btn buttons with data-period="1|2|3"
    // - .pr-value spans with data-interval="1min|3min|5min|10min|20min"
    // - <canvas id="prPowerCurveChart"></canvas>
    // Optional:
    // - <span id="pr-cp"></span>, <span id="pr-wprime"></span>, .pr-curve-subtitle
    // -------------------------
    let prCurveChart = null;

    const PR_INTERVALS = ["1min", "3min", "5min", "10min", "20min"];
    const PR_LABELS = ["1 min", "3 min", "5 min", "10 min", "20 min"];
    const PR_PERIOD_TEXT = { 1: "0–30d", 2: "31–60d", 3: "61–90d" };

    function updatePowerCurveChart(period) {
      const records = data.personalRecords?.[String(period)] || {};
      const canvas = document.getElementById("prPowerCurveChart");

      // Subtitle (optional)
      const subtitle = document.querySelector(".pr-curve-subtitle");
      if (subtitle) subtitle.textContent = `Period: ${PR_PERIOD_TEXT[period] || ""}`;

      // CP / W' proxy (optional)
      const cp = records["20min"] || 0;
      const p1 = records["1min"] || 0;

      const cpEl = document.getElementById("pr-cp");
      const wEl = document.getElementById("pr-wprime");
      if (cpEl) cpEl.textContent = cp > 0 ? `${cp}W` : "—";
      if (wEl) wEl.textContent = cp > 0 && p1 > 0 ? `${Math.max(0, p1 - cp).toFixed(0)} (proxy)` : "—";

      if (!canvas) return;
      if (typeof Chart === "undefined") return;

      const values = PR_INTERVALS.map((k) => records[k] || 0);

      const isDark = document.documentElement.classList.contains("dark");
      const textColor = isDark ? "rgba(229,231,235,0.9)" : "rgba(17,24,39,0.9)";
      const gridColor = isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)";

      destroyChartSafe(prCurveChart);

      prCurveChart = new Chart(canvas, {
        type: "line",
        data: {
          labels: PR_LABELS,
          datasets: [
            {
              label: "Power (W)",
              data: values,
              borderWidth: 2,
              pointRadius: 4,
              pointHoverRadius: 5,
              tension: 0.25,
              fill: false,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => (ctx.parsed.y > 0 ? `${ctx.parsed.y} W` : "No data"),
              },
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { color: textColor, font: { size: 11 } },
              grid: { color: gridColor },
            },
            x: {
              ticks: { color: textColor, font: { size: 11 } },
              grid: { display: false },
            },
          },
        },
      });
    }

    function updatePersonalRecords(period) {
      const records = data.personalRecords?.[String(period)] || {};
      document.querySelectorAll(".pr-value").forEach((el) => {
        const interval = el.dataset.interval;
        const v = records[interval] || 0;
        el.textContent = v > 0 ? v : "—";
        const maybeW = el.nextElementSibling;
        if (maybeW) maybeW.style.display = v > 0 ? "block" : "none";
      });

      updatePowerCurveChart(period);
    }

    bindToggleGroup({
      root: document,
      buttonSelector: ".pr-period-btn",
      activeClasses: ["bg-yellow-400", "dark:bg-yellow-400", "text-gray-900", "dark:text-gray-900"],
      inactiveClasses: ["bg-transparent", "text-gray-600", "dark:text-gray-400"],
      getValue: (btn) => String(btn.dataset.period),
      onChange: (period) => updatePersonalRecords(period),
    });

    // default PR view (match your UI default)
    updatePersonalRecords("1");

    // -------------------------
    // Heart Rate widget
    // -------------------------
    const periodLabels = { 0: "This Month", 1: "1 Month", 2: "2 Months", 3: "3 Months" };

    function updateHeartRate(period) {
      const d = data.heartRate?.[period] || {};
      const cycling = d.Cycling || 0;
      const tread = d.Tread || 0;
      const overall = d.overall || 0;

      setText(document.querySelector(".cycling-hr"), cycling);
      setText(document.querySelector(".tread-hr"), tread);
      setText(document.querySelector(".hr-overall"), overall);

      const cyclingRow = document.querySelector(".hr-cycling-row");
      const treadRow = document.querySelector(".hr-tread-row");
      if (cyclingRow) cyclingRow.style.display = cycling > 0 ? "flex" : "none";
      if (treadRow) treadRow.style.display = tread > 0 ? "flex" : "none";

      const label = document.querySelector(".hr-period-label");
      if (label) label.textContent = periodLabels[period] || "This Month";
    }

    bindToggleGroup({
      root: document,
      buttonSelector: ".hr-period-btn",
      activeClasses: ["bg-primary", "text-white"],
      inactiveClasses: ["bg-gray-100", "dark:bg-gray-700", "text-gray-700", "dark:text-gray-300"],
      getValue: (btn) => Number(btn.dataset.period),
      onChange: (p) => updateHeartRate(p),
    });

    updateHeartRate(0);

    // -------------------------
    // This Month discipline (cycling/running)
    // -------------------------
    bindToggleGroup({
      root: document,
      buttonSelector: ".month-discipline-btn",
      activeClasses: ["bg-primary", "text-white"],
      inactiveClasses: ["bg-gray-100", "dark:bg-gray-700", "text-gray-700", "dark:text-gray-300"],
      getValue: (btn) => btn.dataset.discipline,
      onChange: (discipline) => {
        const showCycling = discipline === "cycling";
        document.querySelectorAll(".cycling-data").forEach((el) => el.classList.toggle("hidden", !showCycling));
        document.querySelectorAll(".running-data").forEach((el) => el.classList.toggle("hidden", showCycling));
      },
    });

    // -------------------------
    // Power to Weight activity
    // -------------------------
    bindToggleGroup({
      root: document,
      buttonSelector: ".pw-activity-btn",
      activeClasses: ["bg-primary", "text-white"],
      inactiveClasses: ["bg-gray-100", "dark:bg-gray-700", "text-gray-700", "dark:text-gray-300"],
      getValue: (btn) => btn.dataset.activity,
      onChange: (activity) => {
        const cycling = activity === "cycling";
        const cc = document.getElementById("pw-cycling-current");
        const tc = document.getElementById("pw-tread-current");
        const ch = document.getElementById("pw-cycling-history");
        const th = document.getElementById("pw-tread-history");

        if (cc) cc.style.display = cycling ? "block" : "none";
        if (tc) tc.style.display = cycling ? "none" : "block";
        if (ch) ch.style.display = cycling ? "block" : "none";
        if (th) th.style.display = cycling ? "none" : "block";
      },
    });

    // -------------------------
    // Charts (Chart.js already loaded via base/_scripts_charts.html)
    // -------------------------
    if (data.hasFtp) {
      createHorizontalBar({
        canvas: document.getElementById("ftpChart"),
        labels: data.ftp?.labels || [],
        values: data.ftp?.values || [],
        tooltipLabel: (ctx) => `${ctx.parsed.x} W`,
      });
    }

    if (data.hasRunningPace) {
      const entries = [...(data.runningPace || [])].sort((a, b) => a.dateSort.localeCompare(b.dateSort));
      createHorizontalBar({
        canvas: document.getElementById("runningPaceChart"),
        labels: entries.map((e) => e.dateStr),
        values: entries.map((e) => e.level),
        tooltipLabel: (ctx) => `Level ${ctx.parsed.x}`,
      });
    }

    if (data.hasWalkingPace) {
      const entries = [...(data.walkingPace || [])].sort((a, b) => a.dateSort.localeCompare(b.dateSort));
      createHorizontalBar({
        canvas: document.getElementById("walkingPaceChart"),
        labels: entries.map((e) => e.dateStr),
        values: entries.map((e) => e.level),
        tooltipLabel: (ctx) => `Level ${ctx.parsed.x}`,
      });
    }

    // -------------------------
    // Time in Zones (compact: 1 chart per sport + monthly/yearly toggle)
    // Requires in your _time_in_zones.html:
    // - cycling:  <canvas id="cyclingZonesChart"></canvas>
    //             <div id="cycling-zones-legend"></div>
    //             <span id="cycling-zones-total-label"></span>
    //             <span id="cycling-zones-total-value"></span>
    // - running:  <canvas id="runningZonesChart"></canvas>
    //             <div id="running-zones-legend"></div>
    //             <span id="running-zones-total-label"></span>
    //             <span id="running-zones-total-value"></span>
    // - Buttons:  .zones-period-btn with data-sport="cycling|running" data-period="month|year"
    // -------------------------
    const zoneCharts = { cycling: null, running: null };

    function periodLabel(period) {
      return period === "year" ? "Past 12 Months:" : "This Month:";
    }

    function getZoneData(sport, period) {
      return data.zones?.[sport]?.[period] || null;
    }

    function setZonesTotal(sport, period) {
      const labelEl =
        sport === "cycling"
          ? document.getElementById("cycling-zones-total-label")
          : document.getElementById("running-zones-total-label");

      const valueEl =
        sport === "cycling"
          ? document.getElementById("cycling-zones-total-value")
          : document.getElementById("running-zones-total-value");

      if (labelEl) labelEl.textContent = periodLabel(period);

      const total = getZoneData(sport, period)?.total_formatted || "00:00:00";
      if (valueEl) valueEl.textContent = total;
    }

    function renderZones(sport, period) {
      const canvas =
        sport === "cycling"
          ? document.getElementById("cyclingZonesChart")
          : document.getElementById("runningZonesChart");

      const legendEl =
        sport === "cycling"
          ? document.getElementById("cycling-zones-legend")
          : document.getElementById("running-zones-legend");

      if (!canvas) return;

      setZonesTotal(sport, period);

      const zoneData = getZoneData(sport, period);
      const colors = sport === "cycling" ? CYCLING_ZONE_COLORS : RUNNING_ZONE_COLORS;

      destroyChartSafe(zoneCharts[sport]);
      zoneCharts[sport] = createDonutZones({
        canvas,
        zoneData,
        colors,
        legendEl,
      });
    }

    document.querySelectorAll(".zones-period-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sport = btn.dataset.sport; // cycling|running
        const period = btn.dataset.period; // month|year

        // style toggles within the sport group
        document.querySelectorAll(`.zones-period-btn[data-sport="${sport}"]`).forEach((b) => {
          b.classList.remove("bg-primary", "text-white");
          b.classList.add("bg-transparent", "text-gray-700", "dark:text-gray-300");
        });

        btn.classList.add("bg-primary", "text-white");
        btn.classList.remove("bg-transparent", "text-gray-700", "dark:text-gray-300");

        renderZones(sport, period);
      });
    });

    // initial zones
    renderZones("cycling", "month");
    renderZones("running", "month");
  } finally {
    showMetricsContent();
    setTimeout(showMetricsContent, 1500);
  }
});