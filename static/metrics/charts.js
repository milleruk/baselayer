export function isDarkMode() {
  return document.documentElement.classList.contains('dark');
}

export function chartTheme() {
  const dark = isDarkMode();
  return {
    dark,
    textColor: dark ? '#e5e7eb' : '#374151',
    gridColor: dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
    tickColor: dark ? '#9ca3af' : '#6b7280',
    tooltipBg: dark ? 'rgba(31,41,55,0.95)' : 'rgba(255,255,255,0.95)',
    tooltipBorder: dark ? 'rgba(75,85,99,1)' : 'rgba(229,231,235,1)'
  };
}

export function createHorizontalBar({ canvas, labels, values, tooltipLabel }) {
  if (!canvas) return null;
  const t = chartTheme();

  return new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: values,
        borderWidth: 1
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: t.tooltipBg,
          titleColor: t.textColor,
          bodyColor: t.textColor,
          borderColor: t.tooltipBorder,
          borderWidth: 1,
          callbacks: {
            label: (ctx) => tooltipLabel(ctx)
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: t.gridColor },
          ticks: { color: t.tickColor }
        },
        y: {
          grid: { display: false },
          ticks: { color: t.tickColor }
        }
      }
    }
  });
}

export function createDonutZones({ canvas, zoneData, colors, legendEl }) {
  if (!canvas || !zoneData?.zones) return null;
  const t = chartTheme();

  const isCycling = typeof zoneData.zones[1] !== 'undefined';
  const cyclingOrder = [1,2,3,4,5,6,7];
  const runningOrder = ['recovery','easy','moderate','challenging','hard','very_hard','max'];
  const order = isCycling ? cyclingOrder : runningOrder;

  const labels = [];
  const values = [];
  const bg = [];

  order.forEach(k => {
    const z = zoneData.zones[k];
    if (!z) return;
    labels.push(z.name);
    values.push(z.time_seconds);
    bg.push(colors[k] || '#888');
  });

  // legend
  if (legendEl) {
    legendEl.innerHTML = '';
    order.forEach((k, idx) => {
      const z = zoneData.zones[k];
      if (!z) return;
      const row = document.createElement('div');
      row.className = 'flex items-center justify-between text-sm';
      row.innerHTML = `
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full" style="background-color:${bg[idx]};"></div>
          <span class="text-gray-700 dark:text-gray-300">${z.name}</span>
        </div>
        <span class="text-gray-600 dark:text-gray-400 font-medium">${z.time_formatted}</span>
      `;
      legendEl.appendChild(row);
    });
  }

  return new Chart(canvas, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: bg, borderWidth: 0 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: t.tooltipBg,
          titleColor: t.textColor,
          bodyColor: t.textColor,
          borderColor: t.tooltipBorder,
          borderWidth: 1,
          callbacks: {
            label: (ctx) => {
              const total = ctx.dataset.data.reduce((a,b)=>a+b,0);
              const v = ctx.parsed || 0;
              const pct = total ? ((v/total)*100).toFixed(1) : '0.0';
              const k = order[ctx.dataIndex];
              const z = zoneData.zones[k];
              return `${z.name}: ${z.time_formatted} (${pct}%)`;
            }
          }
        }
      },
      cutout: '60%'
    }
  });
}