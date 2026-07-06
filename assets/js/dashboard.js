document.addEventListener("DOMContentLoaded", () => {
  const data = window.REPORT_DATA || { daily: [], campaigns: [], conversionName: "Conversions" };
  const orange = "#ff530d";
  const black = "#0f0f0f";
  let trendChart;
  let spendChart;

  const fmtEuro = v => "€" + Number(v || 0).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2});
  const fmtInt = v => Math.round(Number(v || 0)).toLocaleString();
  const fmtPct = v => Number(v || 0).toFixed(2) + "%";

  function parseDate(s){ return new Date(s + "T00:00:00"); }
  function iso(d){ return d.toISOString().slice(0,10); }

  function latestDate(rows){
    return rows.reduce((max, r) => !max || r.date > max ? r.date : max, null);
  }

  function monthStart(d){ return new Date(d.getFullYear(), d.getMonth(), 1); }
  function monthEnd(d){ return new Date(d.getFullYear(), d.getMonth() + 1, 0); }

  function rangeFromSelection(){
    const rows = data.daily || [];
    const latest = latestDate(rows);
    const select = document.getElementById("dateRange");
    const value = select ? select.value : "30";
    const customWrap = document.getElementById("customDateWrap");
    if(customWrap) customWrap.style.display = value === "custom" ? "flex" : "none";

    if(!latest) return {start:null, end:null, label:"No data"};

    const endBase = parseDate(latest);
    let start, end, label;

    if(value === "this_month"){
      start = monthStart(endBase);
      end = endBase;
      label = "This month";
    } else if(value === "last_month"){
      const lastMonth = new Date(endBase.getFullYear(), endBase.getMonth() - 1, 1);
      start = monthStart(lastMonth);
      end = monthEnd(lastMonth);
      label = "Last month";
    } else if(value === "custom"){
      const cs = document.getElementById("customStart")?.value;
      const ce = document.getElementById("customEnd")?.value;
      start = cs ? parseDate(cs) : new Date(endBase.getFullYear(), endBase.getMonth(), 1);
      end = ce ? parseDate(ce) : endBase;
      label = `${iso(start)} to ${iso(end)}`;
    } else {
      const days = Number(value || 30);
      end = endBase;
      start = new Date(end);
      start.setDate(start.getDate() - days + 1);
      label = days === 365 ? "Last 12 months" : `Last ${days} days`;
    }

    return {start, end, label};
  }

  function filterByRange(start, end){
    if(!start || !end) return [];
    return (data.daily || []).filter(r => {
      const d = parseDate(r.date);
      return d >= start && d <= end;
    });
  }

  function previousRange(start, end){
    const ms = end - start;
    const prevEnd = new Date(start);
    prevEnd.setDate(prevEnd.getDate() - 1);
    const prevStart = new Date(prevEnd.getTime() - ms);
    return {start: prevStart, end: prevEnd};
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

  function compareText(current, previous){
    if(!previous) return "";
    const pct = ((current - previous) / previous) * 100;
    const up = pct >= 0;
    return `<span class="${up ? "up" : "down"}">${up ? "▲" : "▼"} ${Math.abs(pct).toFixed(1)}%</span> vs previous`;
  }

  function updateKpis(summary, previous, compare){
    const map = {
      spend: [fmtEuro(summary.spend), summary.spend, previous.spend],
      conversions: [fmtInt(summary.conversions), summary.conversions, previous.conversions],
      cost_per_conversion: [fmtEuro(summary.cost_per_conversion), summary.cost_per_conversion, previous.cost_per_conversion],
      ctr: [fmtPct(summary.ctr), summary.ctr, previous.ctr],
      cpc: [fmtEuro(summary.cpc), summary.cpc, previous.cpc],
      reach: [fmtInt(summary.reach), summary.reach, previous.reach],
      impressions: [fmtInt(summary.impressions), summary.impressions, previous.impressions],
      clicks: [fmtInt(summary.clicks), summary.clicks, previous.clicks]
    };

    Object.entries(map).forEach(([key, values]) => {
      const card = document.querySelector(`[data-kpi="${key}"]`);
      if(!card) return;
      card.querySelector(".kpi-value").textContent = values[0];
      const c = card.querySelector(".kpi-compare");
      if(c) c.innerHTML = compare ? compareText(values[1], values[2]) : "";
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
    const range = rangeFromSelection();
    const rows = filterByRange(range.start, range.end);
    const prev = previousRange(range.start, range.end);
    const prevRows = filterByRange(prev.start, prev.end);
    const summary = summarise(rows);
    const previous = summarise(prevRows);
    const compare = document.getElementById("compareToggle").checked;

    document.getElementById("rangeLabel").textContent = range.label;
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

  document.getElementById("campaignSearch")?.addEventListener("input", e => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll("#campaignTable tbody tr").forEach(row => {
      row.style.display = row.innerText.toLowerCase().includes(q) ? "" : "none";
    });
  });

  document.getElementById("dateRange")?.addEventListener("change", refresh);
  document.getElementById("compareToggle")?.addEventListener("change", refresh);
  document.getElementById("customStart")?.addEventListener("change", refresh);
  document.getElementById("customEnd")?.addEventListener("change", refresh);

  refresh();
});
