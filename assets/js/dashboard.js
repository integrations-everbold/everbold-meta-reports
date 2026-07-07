document.addEventListener("DOMContentLoaded", () => {
  const data = window.REPORT_DATA || { daily: [], campaigns: [], conversionName: "Conversions" };
  const orange = "#ff530d";
  const black = "#0f0f0f";

  document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", () => {
      document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
      link.classList.add("active");
    });
  });

  const search = document.getElementById("campaignSearch");
  if (search) {
    search.addEventListener("input", () => {
      const q = search.value.toLowerCase();
      document.querySelectorAll("#campaignTable tbody tr").forEach(row => {
        row.style.display = row.innerText.toLowerCase().includes(q) ? "" : "none";
      });
    });
  }

  const trendCanvas = document.getElementById("trendChart");
  if (trendCanvas && data.daily && data.daily.length) {
    new Chart(trendCanvas, {
      type: "line",
      data: {
        labels: data.daily.map(d => d.date),
        datasets: [
          {
            label: "Spend",
            data: data.daily.map(d => d.spend),
            borderColor: orange,
            backgroundColor: "rgba(255,83,13,.12)",
            tension: .35,
            fill: true,
            yAxisID: "y"
          },
          {
            label: data.conversionName,
            data: data.daily.map(d => d.conversions),
            borderColor: black,
            backgroundColor: "rgba(15,15,15,.08)",
            tension: .35,
            fill: false,
            yAxisID: "y1"
          }
        ]
      },
      options: {
        responsive: true,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { position: "bottom" } },
        scales: {
          y: { beginAtZero: true },
          y1: { beginAtZero: true, position: "right", grid: { drawOnChartArea: false } },
          x: { grid: { display: false } }
        }
      }
    });
  }

  const top = [...(data.campaigns || [])].sort((a,b) => b.spend - a.spend).slice(0, 6);
  const spendCanvas = document.getElementById("campaignSpendChart");
  if (spendCanvas && top.length) {
    new Chart(spendCanvas, {
      type: "doughnut",
      data: {
        labels: top.map(c => c.name),
        datasets: [{
          data: top.map(c => c.spend),
          backgroundColor: [orange, "#111", "#ff8b54", "#777", "#ffc2a8", "#ddd"]
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: "bottom", labels: { boxWidth: 10 } } }
      }
    });
  }
});
