document.addEventListener("DOMContentLoaded", () => {
  const data = window.REPORT_DATA || { campaigns: [], conversionName: "Conversions" };
  const orange = "#ff530d";

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

  const conversionCanvas = document.getElementById("campaignConversionChart");
  if (conversionCanvas && top.length) {
    new Chart(conversionCanvas, {
      type: "bar",
      data: {
        labels: top.map(c => c.name),
        datasets: [{
          label: data.conversionName,
          data: top.map(c => c.conversions),
          backgroundColor: orange
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { display: false }, grid: { display: false } },
          y: { beginAtZero: true }
        }
      }
    });
  }
});
