// static/js/dashboard.js
console.log("Dashboard JS loaded");

(function () {
  let chartInstances = { frequency: null, type: null, trends: null };

  function prefersDark() {
    return document.documentElement.classList.contains("dark");
  }

  function getChartData() {
    const el = document.getElementById("chart-data");
    if (!el) return null;
    try {
      return JSON.parse(el.textContent || "{}");
    } catch {
      return null;
    }
  }

  function destroyCharts() {
    Object.keys(chartInstances).forEach((k) => {
      if (chartInstances[k]) {
        chartInstances[k].destroy();
        chartInstances[k] = null;
      }
    });
  }

  function initCharts() {
    // Chart.js not loaded yet
    if (typeof Chart === "undefined") return;

    const chartData = getChartData();
    if (!chartData) {
      // This is the #1 reason charts "don't load after HTMX"
      console.warn("No #chart-data found in DOM after swap; charts not initialised.");
      destroyCharts();
      return;
    }

    const isDark = prefersDark();
    const textColor = isDark ? "rgba(255, 255, 255, 0.8)" : "rgba(0, 0, 0, 0.8)";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

    const workouts_by_week = chartData.workouts_by_week || [];
    const workouts_by_type = chartData.workouts_by_type || {};
    const running_workouts_by_week = chartData.running_workouts_by_week || [];

    destroyCharts();

    // Workout Frequency (bar)
    const frequencyCanvas = document.getElementById("workoutFrequencyChart");
    if (frequencyCanvas) {
      const labels = workouts_by_week.map((w) => {
        const d = new Date(w.date);
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      });
      const counts = workouts_by_week.map((w) => w.count);

      chartInstances.frequency = new Chart(frequencyCanvas, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Workouts",
              data: counts,
              backgroundColor: "rgba(59, 130, 246, 0.6)",
              borderColor: "rgb(59, 130, 246)",
              borderWidth: 1,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false } },
          scales: {
            y: { beginAtZero: true, ticks: { stepSize: 1, color: textColor }, grid: { color: gridColor } },
            x: { ticks: { color: textColor }, grid: { display: false } },
          },
        },
      });
    }

    // Workout Type Breakdown (doughnut)
    const typeCanvas = document.getElementById("workoutTypeChart");
    if (typeCanvas) {
      const typeLabels = Object.keys(workouts_by_type);
      const typeCounts = Object.values(workouts_by_type);

      const colors = [
        "rgba(59, 130, 246, 0.8)",
        "rgba(34, 197, 94, 0.8)",
        "rgba(234, 179, 8, 0.8)",
        "rgba(239, 68, 68, 0.8)",
        "rgba(168, 85, 247, 0.8)",
        "rgba(236, 72, 153, 0.8)",
        "rgba(14, 165, 233, 0.8)",
        "rgba(251, 146, 60, 0.8)",
      ];

      chartInstances.type = new Chart(typeCanvas, {
        type: "doughnut",
        data: { labels: typeLabels, datasets: [{ data: typeCounts, backgroundColor: colors.slice(0, typeLabels.length), borderWidth: 2, borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,1)" }] },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "bottom", labels: { color: textColor, padding: 15 } },
            tooltip: {
              callbacks: {
                label: function (context) {
                  const label = context.label || "";
                  const value = context.parsed || 0;
                  const total = context.dataset.data.reduce((a, b) => a + b, 0);
                  const percentage = total ? ((value / total) * 100).toFixed(1) : "0.0";
                  return `${label}: ${value} (${percentage}%)`;
                },
              },
            },
          },
        },
      });
    }

    // Output & Calories Trends (line)
    const trendsCanvas = document.getElementById("outputTrendsChart");
    if (trendsCanvas) {
      const labels = workouts_by_week.map((w) => {
        const d = new Date(w.date);
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      });
      const outputData = workouts_by_week.map((w) => w.total_output || 0);
      const caloriesData = workouts_by_week.map((w) => w.total_calories || 0);

      chartInstances.trends = new Chart(trendsCanvas, {
        type: "line",
        data: {
          labels,
          datasets: [
            { label: "Total Output (kJ)", data: outputData, borderColor: "rgb(59,130,246)", backgroundColor: "rgba(59,130,246,0.1)", yAxisID: "y", tension: 0.4, fill: true },
            { label: "Total Calories", data: caloriesData, borderColor: "rgb(239,68,68)", backgroundColor: "rgba(239,68,68,0.1)", yAxisID: "y1", tension: 0.4, fill: true },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: { legend: { position: "top", labels: { color: textColor } }, tooltip: { mode: "index", intersect: false } },
          scales: {
            x: { ticks: { color: textColor }, grid: { color: gridColor } },
            y: { type: "linear", display: true, position: "left", title: { display: true, text: "Output (kJ)", color: textColor }, ticks: { color: textColor }, grid: { color: gridColor } },
            y1: { type: "linear", display: true, position: "right", title: { display: true, text: "Calories", color: textColor }, ticks: { color: textColor }, grid: { drawOnChartArea: false } },
          },
        },
      });
    }

    // Running Trends Chart (line)
    const runningTrendsCanvas = document.getElementById("runningTrendsChart");
    if (runningTrendsCanvas) {
      const labels = running_workouts_by_week.map((w) => {
        const d = new Date(w.date);
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      });
      const distanceData = running_workouts_by_week.map((w) => w.distance || 0);
      const caloriesData = running_workouts_by_week.map((w) => w.calories || 0);

      chartInstances.runningTrends = new Chart(runningTrendsCanvas, {
        type: "line",
        data: {
          labels,
          datasets: [
            { label: "Distance (mi)", data: distanceData, borderColor: "rgb(34,197,94)", backgroundColor: "rgba(34,197,94,0.1)", yAxisID: "y", tension: 0.4, fill: true },
            { label: "Calories", data: caloriesData, borderColor: "rgb(239,68,68)", backgroundColor: "rgba(239,68,68,0.1)", yAxisID: "y1", tension: 0.4, fill: true },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: { legend: { position: "top", labels: { color: textColor } }, tooltip: { mode: "index", intersect: false } },
          scales: {
            x: { ticks: { color: textColor }, grid: { color: gridColor } },
            y: { type: "linear", display: true, position: "left", title: { display: true, text: "Distance (mi)", color: textColor }, ticks: { color: textColor }, grid: { color: gridColor } },
            y1: { type: "linear", display: true, position: "right", title: { display: true, text: "Calories", color: textColor }, ticks: { color: textColor }, grid: { drawOnChartArea: false } },
          },
        },
      });
    }
  }

  function updateActiveButton(period) {
    document.querySelectorAll(".period-filter").forEach((btn) => {
      const btnPeriod = btn.getAttribute("data-period");
      if (btnPeriod === period) {
        btn.classList.add("bg-primary", "text-white", "shadow");
        btn.classList.remove("text-gray-700", "dark:text-gray-300", "hover:bg-gray-100/80", "dark:hover:bg-gray-700/60");
      } else {
        btn.classList.remove("bg-primary", "text-white", "shadow");
        btn.classList.add("text-gray-700", "dark:text-gray-300", "hover:bg-gray-100/80", "dark:hover:bg-gray-700/60");
      }
    });
  }

  // Used by the checkbox in dashboard_content.html
  window.toggleHideManual = function (checkbox) {
    const url = new URL(window.location.href);

    if (checkbox.checked) url.searchParams.set("hide_manual", "1");
    else url.searchParams.delete("hide_manual");

    if (!url.searchParams.get("period")) {
      const active = document.querySelector(".period-filter.bg-primary");
      url.searchParams.set("period", active?.getAttribute("data-period") || "7d");
    }

    if (window.htmx) {
      window.htmx.ajax("GET", url.toString(), { target: "#dashboard-content", swap: "innerHTML" });
    } else {
      window.location.href = url.toString();
    }
  };

  function attachPeriodFilterListeners() {
    document.querySelectorAll(".period-filter").forEach((btn) => {
      btn.addEventListener("click", function () {
        const period = this.getAttribute("data-period") || "7d";
        updateActiveButton(period);
      });
    });
  }

  function boot() {
    // init once on full load
    initCharts();
    attachPeriodFilterListeners();
  }

  document.addEventListener("DOMContentLoaded", boot);

  // HTMX: re-init after swaps (content OR shell)
  document.body.addEventListener('htmx:afterSwap', function (event) {
    if (!event.detail || !event.detail.target) return;
    if (event.detail.target.id !== 'dashboard-shell') return;

    window.setTimeout(() => {
      initCharts();
      attachPeriodFilterListeners();
    }, 80);

    const xhr = event.detail.xhr;
    if (xhr && xhr.responseURL) {
      const url = new URL(xhr.responseURL);
      const period = url.searchParams.get('period') || '7d';
      updateActiveButton(period);
    }
  });

  // HTMX: fires when it processes newly added content
  document.body.addEventListener("htmx:load", function (event) {
    const el = event.detail && event.detail.elt;
    if (!el) return;

    if (el.id === "dashboard-content" || el.id === "dashboard-shell" || el.querySelector?.("#dashboard-content")) {
      window.setTimeout(() => {
        initCharts();
        attachPeriodFilterListeners();
      }, 50);
    }
  });

  // Cleanup before swapping charts away
  document.body.addEventListener("htmx:beforeSwap", function (event) {
    const t = event.detail && event.detail.target;
    if (!t) return;
    if (t.id === "dashboard-content" || t.id === "dashboard-shell") destroyCharts();
  });
})();

function showGlobalLoader() {
  var loader = document.getElementById('global-loader');
  if (loader) loader.classList.remove('hidden');
  if (window.setRandomLoaderMessage) window.setRandomLoaderMessage();
}

function hideGlobalLoader() {
  var loader = document.getElementById('global-loader');
  if (loader) loader.classList.add('hidden');
}

// Show loader on initial dashboard load
if (document.readyState === 'loading') {
  showGlobalLoader();
} else {
  showGlobalLoader();
}

document.addEventListener('DOMContentLoaded', function () {
  hideGlobalLoader();
});

// Hide loader after HTMX swaps (full shell reload)
document.body.addEventListener('htmx:afterSwap', function (event) {
  if (!event.detail || !event.detail.target) return;
  if (event.detail.target.id === 'dashboard-shell') {
    hideGlobalLoader();
  }
});