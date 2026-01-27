// Eddington page chart initialization
document.addEventListener('DOMContentLoaded', function() {
  // Times Completed vs Distance Chart
  const timesCompletedDataEl = document.getElementById('times-completed-data');
  if (timesCompletedDataEl) {
    const timesCompletedData = JSON.parse(timesCompletedDataEl.textContent);
    const currentEddingtonEl = document.getElementById('current-eddington');
    const currentEddington = currentEddingtonEl ? parseInt(JSON.parse(currentEddingtonEl.textContent)) : 0;
    
    const ctx = document.getElementById('times-completed-chart');
    if (ctx) {
      const labels = timesCompletedData.map(d => d.distance);
      const timesCompleted = timesCompletedData.map(d => d.times_completed);
      
      // Eddington line is the diagonal y = x (where times_completed = distance)
      const eddingtonLineData = timesCompletedData.map(d => d.distance);
      
      // Check if dark mode is enabled
      const isDark = document.documentElement.classList.contains('dark');
      const textColor = isDark ? 'rgba(209, 213, 219, 0.7)' : 'rgba(107, 114, 128, 0.7)';
      const gridColor = isDark ? 'rgba(209, 213, 219, 0.1)' : 'rgba(107, 114, 128, 0.1)';
      const tooltipBg = isDark ? 'rgba(31, 41, 55, 0.95)' : 'rgba(255, 255, 255, 0.95)';
      const tooltipBorder = isDark ? 'rgba(209, 213, 219, 0.2)' : 'rgba(107, 114, 128, 0.2)';
      
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Times completed',
              data: timesCompleted,
              backgroundColor: 'rgba(249, 115, 22, 0.6)',
              borderColor: 'rgba(249, 115, 22, 1)',
              borderWidth: 1,
              order: 2
            },
            {
              label: 'Eddington',
              data: eddingtonLineData,
              type: 'line',
              borderColor: 'rgba(249, 115, 22, 1)',
              borderWidth: 2,
              pointRadius: function(context) {
                const index = context.dataIndex;
                if (labels[index] === currentEddington) {
                  return 8;
                }
                return 4;
              },
              pointBackgroundColor: 'rgba(249, 115, 22, 1)',
              pointBorderColor: isDark ? '#1f2937' : '#ffffff',
              pointBorderWidth: 2,
              pointHoverRadius: 8,
              fill: false,
              order: 1
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top',
              labels: {
                color: textColor,
                usePointStyle: true
              }
            },
            tooltip: {
              backgroundColor: tooltipBg,
              borderColor: tooltipBorder,
              borderWidth: 1,
              titleColor: isDark ? '#ffffff' : '#111827',
              bodyColor: textColor,
              padding: 12,
              callbacks: {
                title: function(context) {
                  return `${context[0].label} km`;
                },
                label: function(context) {
                  if (context.datasetIndex === 0) {
                    return `Times completed: ${context.parsed.y}`;
                  } else {
                    if (parseInt(context.label) === currentEddington) {
                      return `Current Eddington: ${currentEddington}`;
                    }
                    return `Eddington line`;
                  }
                }
              }
            }
          },
          scales: {
            x: {
              title: {
                display: true,
                text: 'Distance (km)',
                color: textColor
              },
              grid: {
                color: gridColor
              },
              ticks: {
                color: textColor,
                maxTicksLimit: 20,
                callback: function(value, index) {
                  if (index % 6 === 0 || index === labels.length - 1) {
                    return labels[index];
                  }
                  return '';
                }
              }
            },
            y: {
              title: {
                display: true,
                text: 'Times completed',
                color: textColor
              },
              beginAtZero: true,
              grid: {
                color: gridColor
              },
              ticks: {
                color: textColor,
                precision: 0
              }
            }
          }
        }
      });
    }
  }
  
  // Eddington History Chart
  const historyDataEl = document.getElementById('eddington-history-data');
  if (historyDataEl) {
    const historyData = JSON.parse(historyDataEl.textContent);
    
    const ctx = document.getElementById('eddington-history-chart');
    if (ctx) {
      const dates = historyData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      });
      const datesShort = historyData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-GB', { month: 'short', year: 'numeric' });
      });
      const eddingtonNumbers = historyData.map(d => d.eddington_number);
      
      // Check if dark mode is enabled
      const isDark = document.documentElement.classList.contains('dark');
      const textColor = isDark ? 'rgba(209, 213, 219, 0.7)' : 'rgba(107, 114, 128, 0.7)';
      const gridColor = isDark ? 'rgba(209, 213, 219, 0.1)' : 'rgba(107, 114, 128, 0.1)';
      const tooltipBg = isDark ? 'rgba(31, 41, 55, 0.95)' : 'rgba(255, 255, 255, 0.95)';
      const tooltipBorder = isDark ? 'rgba(209, 213, 219, 0.2)' : 'rgba(107, 114, 128, 0.2)';
      
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: datesShort,
          datasets: [{
            label: 'Eddington Number',
            data: eddingtonNumbers,
            borderColor: 'rgba(249, 115, 22, 1)',
            backgroundColor: 'rgba(249, 115, 22, 0.1)',
            borderWidth: 2,
            pointRadius: 4,
            pointBackgroundColor: 'rgba(249, 115, 22, 1)',
            pointBorderColor: isDark ? '#1f2937' : '#ffffff',
            pointBorderWidth: 2,
            pointHoverRadius: 6,
            fill: true,
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top',
              labels: {
                color: textColor,
                usePointStyle: true
              }
            },
            tooltip: {
              backgroundColor: tooltipBg,
              borderColor: tooltipBorder,
              borderWidth: 1,
              titleColor: isDark ? '#ffffff' : '#111827',
              bodyColor: textColor,
              padding: 12,
              callbacks: {
                title: function(context) {
                  const index = context[0].dataIndex;
                  return dates[index];
                },
                label: function(context) {
                  return `Eddington Number: ${context.parsed.y}`;
                }
              }
            }
          },
          scales: {
            x: {
              title: {
                display: true,
                text: 'Date',
                color: textColor
              },
              grid: {
                color: gridColor
              },
              ticks: {
                color: textColor,
                maxTicksLimit: 12,
                callback: function(value, index) {
                  if (index % Math.ceil(datesShort.length / 12) === 0 || index === datesShort.length - 1) {
                    return datesShort[index];
                  }
                  return '';
                }
              }
            },
            y: {
              title: {
                display: true,
                text: 'Eddington Number',
                color: textColor
              },
              beginAtZero: true,
              grid: {
                color: gridColor
              },
              ticks: {
                color: textColor,
                precision: 0,
                stepSize: 10
              }
            }
          }
        }
      });
    }
  }
});
