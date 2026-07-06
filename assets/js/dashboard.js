document.addEventListener("DOMContentLoaded", () => {
  const data = window.REPORT_DATA || { daily: [], campaigns: [], conversionName: "Conversions" };
  const orange = "#ff530d";
  const black = "#0f0f0f";
  let trendChart;
  let spendChart;

  const fmtEuro = v => "€" + Number(v || 0).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2});
  const fmtInt = v => Math.round(Number(v || 0)).toLocaleString();
  const fmtPct = v => Number(v || 0).toFixed(2) + "%";

  function score(summary){
    let s = 100;
    if(summary.ctr < 1) s -= 24; else if(summary.ctr < 1.5) s -= 14; else if(summary.ctr < 2) s -= 6;
    if(summary.cpc > 2) s -= 18; else if(summary.cpc > 1) s -= 8;
    if(summary.cost_per_conversion > 50) s -= 18; else if(summary.cost_per_conversion > 30) s -= 8;
    return Math.max(0, Math.min(100, Math.round(s)));
  }

  function health(s){
    if(s >= 88) return "Excellent";
    if(s >= 74) return "Strong";
    if(s >= 60) return "Stable";
    return "Needs Attention";
  }

  function latestDate(rows){
    return rows.reduce((max, r) => !max || r.date > max ? r.date : max, null);
  }

  function filterDays(days, offsetPeriods = 0){
    const rows = data.daily || [];
    const endStr = latestDate(rows);
    if(!endStr) return [];
    const end = new Date(endStr + "T00:00:00");
    end.setDate(end.getDate() - (days * offsetPeriods));
    const start = new Date(end);
    start.setDate(start.getDate() - days + 1);
    return rows.filter(r => {
      const d = new Date(r.date + "T00:00:00");
      return d >= start && d <= end;
    });
  }

  function summarise(rows){
    const sum = rows.reduce((a,r) => {
      a.spend += Number(r.spend || 0);
      a.conversions += Number(r.conversions || 0);
      a.clicks += Number(r.clicks || 0);
      a.impressions += Number(r.impressions || 0);
      a.reach += Number(r.reach || 0);
      return a;
    }, {spend:0, conversions:0, clicks:0, impressions:0, reach:0});
    sum.ctr = sum.impressions ? (sum.clicks / sum.impressions) * 100 : 0;
    sum.cpc = sum.clicks ? sum.spend / sum.clicks : 0;
    sum.cost_per_conversion = sum.conversions ? sum.spend / sum.conversions : 0;
    return sum;
  }

  function compareText(current, previous, type){
    if(!previous && previous !== 0) return "";
    const diff = current - previous;
    const pct = previous ? (diff / previous) * 100 : 0;
    const up = diff >= 0;
    const cls = up ? "up" : "down";
    if(type === "cost") return `<span class="${cls}">${up ? "▲" : "▼"} ${Math.abs(pct).toFixed(1)}%</span> vs previous`;
    return `<span class="${cls}">${up ? "▲" : "▼"} ${Math.abs(pct).toFixed(1)}%</span> vs previous`;
  }

  function updateKpis(summary, previous, compare){
    const map = {
      spend: [fmtEuro(summary.spend), summary.spend, previous.spend, "money"],
      conversions: [fmtInt(summary.conversions), summary.conversions, previous.conversions, "number"],
      cost_per_conversion: [fmtEuro(summary.cost_per_conversion), summary.cost_per_conversion, previous.cost_per_conversion, "cost"],
      ctr: [fmtPct(summary.ctr), summary.ctr, previous.ctr, "pct"],
      cpc: [fmtEuro(summary.cpc), summary.cpc, previous.cpc, "cost"],
      reach: [fmtInt(summary.reach), summary.reach, previous.reach, "number"],
      impressions: [fmtInt(summary.impressions), summary.impressions, previous.impressions, "number"],
      clicks: [fmtInt(summary.clicks), summary.clicks, previous.clicks, "number"]
    };

    Object.entries(map).forEach(([key, values]) => {
      const card = document.querySelector(`[data-kpi="${key}"]`);
      if(!card) return;
      card.querySelector(".kpi-value").textContent = values[0];
      const c = card.querySelector(".kpi-compare");
      c.innerHTML = compare ? compareText(values[1], values[2], values[3]) : "";
    });

    const s = score(summary);
    document.getElementById("scoreValue").textContent = s;
    document.getElementById("scoreHealth").textContent = health(s);
    document.getElementById("summaryTitle").textContent = `${health(s)} Meta Performance`;
    document.getElementById("summaryText").textContent = `${data.clientName} generated ${fmtInt(summary.conversions)} ${data.conversionName} from ${fmtEuro(summary.spend)} in Meta spend. The average cost per ${data.conversionName.toLowerCase()} was ${fmtEuro(summary.cost_per_conversion)}, with a CTR of ${fmtPct(summary.ctr)}.`;
  }

  function renderTrend(rows, previousRows, compare){
    const ctx = document.getElementById("trendChart");
    if(!ctx) return;
    if(trendChart) trendChart.destroy();

    const datasets = [
      {label:"Spend", data: rows.map(r => r.spend), borderColor:orange, backgroundColor:"rgba(255,83,13,.12)", tension:.35, fill:true, yAxisID:"y"},
      {label:data.conversionName, data: rows.map(r => r.conversions), borderColor:black, backgroundColor:"rgba(15,15,15,.08)", tension:.35, fill:false, yAxisID:"y1"}
    ];

    if(compare && previousRows.length){
      datasets.push({label:"Previous spend", data: previousRows.map(r => r.spend), borderColor:"#999", borderDash:[6,6], tension:.35, fill:false, yAxisID:"y"});
      datasets.push({label:`Previous ${data.conversionName}`, data: previousRows.map(r => r.conversions), borderColor:"#bbb", borderDash:[6,6], tension:.35, fill:false, yAxisID:"y1"});
    }

    trendChart = new Chart(ctx, {
      type:"line",
      data:{labels:rows.map(r => r.date), datasets},
      options:{responsive:true, interaction:{mode:"index",intersect:false}, plugins:{legend:{position:"bottom"}}, scales:{y:{beginAtZero:true}, y1:{beginAtZero:true,position:"right",grid:{drawOnChartArea:false}}, x:{grid:{display:false}}}}
    });
  }

  function renderSpend(){
    const ctx = document.getElementById("campaignSpendChart");
    if(!ctx || spendChart) return;
    const top = [...(data.campaigns || [])].sort((a,b) => b.spend - a.spend).slice(0,6);
    spendChart = new Chart(ctx, {
      type:"doughnut",
      data:{labels:top.map(c=>c.name), datasets:[{data:top.map(c=>c.spend), backgroundColor:[orange,"#111","#ff8b54","#777","#ffc2a8","#ddd"]}]},
      options:{responsive:true, plugins:{legend:{position:"bottom", labels:{boxWidth:10}}}}
    });
  }

  function refresh(){
    const days = Number(document.getElementById("dateRange").value || 30);
    const compare = document.getElementById("compareToggle").checked;
    const rows = filterDays(days, 0);
    const prevRows = filterDays(days, 1);
    const summary = summarise(rows);
    const previous = summarise(prevRows);

    document.getElementById("rangeLabel").textContent = `Last ${days === 365 ? "12 months" : days + " days"}`;
    updateKpis(summary, previous, compare);
    renderTrend(rows, prevRows, compare);
    renderSpend();
  }

  document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", () => {
      document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
      link.classList.add("active");
    });
  });

  const search = document.getElementById("campaignSearch");
  if(search){
    search.addEventListener("input", () => {
      const q = search.value.toLowerCase();
      document.querySelectorAll("#campaignTable tbody tr").forEach(row => {
        row.style.display = row.innerText.toLowerCase().includes(q) ? "" : "none";
      });
    });
  }

  document.getElementById("dateRange")?.addEventListener("change", refresh);
  document.getElementById("compareToggle")?.addEventListener("change", refresh);
  refresh();
});
