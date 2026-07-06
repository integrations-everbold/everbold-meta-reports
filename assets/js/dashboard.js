document.addEventListener("DOMContentLoaded", () => {
  const data = window.REPORT_DATA || {};
  const orange = "#ff530d";
  const black = "#0f0f0f";
  let trendChart, spendChart;

  const fmtEuro = v => "€" + Number(v || 0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
  const fmtInt = v => Math.round(Number(v || 0)).toLocaleString();
  const fmtPct = v => Number(v || 0).toFixed(2) + "%";
  const parseDate = s => new Date(s + "T00:00:00");
  const iso = d => d.toISOString().slice(0,10);
  const latestDate = rows => rows.reduce((m,r)=>!m||r.date>m?r.date:m,null);

  function rangeFromSelection(){
    const rows = data.daily || [];
    const latest = latestDate(rows);
    const value = document.getElementById("dateRange")?.value || "30";
    const customWrap = document.getElementById("customDateWrap");
    if(customWrap) customWrap.style.display = value === "custom" ? "flex" : "none";
    if(!latest) return {start:null,end:null,label:"No data"};

    const endBase = parseDate(latest);
    let start, end, label;
    if(value === "this_month"){
      start = new Date(endBase.getFullYear(), endBase.getMonth(), 1);
      end = endBase;
      label = "This month";
    } else if(value === "last_month"){
      start = new Date(endBase.getFullYear(), endBase.getMonth()-1, 1);
      end = new Date(endBase.getFullYear(), endBase.getMonth(), 0);
      label = "Last month";
    } else if(value === "custom"){
      start = document.getElementById("customStart")?.value ? parseDate(document.getElementById("customStart").value) : new Date(endBase.getFullYear(), endBase.getMonth(), 1);
      end = document.getElementById("customEnd")?.value ? parseDate(document.getElementById("customEnd").value) : endBase;
      label = `${iso(start)} to ${iso(end)}`;
    } else {
      const days = Number(value || 30);
      end = endBase;
      start = new Date(end);
      start.setDate(start.getDate()-days+1);
      label = days === 365 ? "Last 12 months" : `Last ${days} days`;
    }
    return {start,end,label};
  }

  function filterRows(rows,start,end){
    if(!start||!end) return [];
    return (rows||[]).filter(r => {
      const d = parseDate(r.date);
      return d >= start && d <= end;
    });
  }

  function previousRange(start,end){
    const ms = end - start;
    const prevEnd = new Date(start);
    prevEnd.setDate(prevEnd.getDate()-1);
    const prevStart = new Date(prevEnd.getTime()-ms);
    return {start:prevStart,end:prevEnd};
  }

  function summarise(rows){
    const s = rows.reduce((a,r)=>{
      a.spend += Number(r.spend||0); a.conversions += Number(r.conversions||0); a.clicks += Number(r.clicks||0); a.impressions += Number(r.impressions||0); a.reach += Number(r.reach||0);
      return a;
    }, {spend:0,conversions:0,clicks:0,impressions:0,reach:0});
    s.ctr = s.impressions ? (s.clicks/s.impressions)*100 : 0;
    s.cpc = s.clicks ? s.spend/s.clicks : 0;
    s.cost_per_conversion = s.conversions ? s.spend/s.conversions : 0;
    return s;
  }

  function aggregateCampaigns(rows){
    const map = {};
    rows.forEach(r => {
      const key = r.campaign_id || r.name;
      if(!map[key]) map[key] = {name:r.name,status:r.status||"Active",spend:0,conversions:0,clicks:0,impressions:0,reach:0};
      const a = map[key];
      a.spend += Number(r.spend||0); a.conversions += Number(r.conversions||0); a.clicks += Number(r.clicks||0); a.impressions += Number(r.impressions||0); a.reach += Number(r.reach||0);
    });
    return Object.values(map).map(a => ({...a, ctr:a.impressions?(a.clicks/a.impressions)*100:0, cpc:a.clicks?a.spend/a.clicks:0, cost_per_conversion:a.conversions?a.spend/a.conversions:0})).sort((a,b)=>b.spend-a.spend);
  }

  function aggregateCreatives(rows){
    const sourceRows = (rows && rows.length) ? rows : (data.creatives || []);
    const map = {};
    sourceRows.forEach(r => {
      const key = r.ad_id || r.ad_name;
      if(!map[key]) {
        map[key] = {
          ad_id:r.ad_id,
          ad_name:r.ad_name,
          status:r.status,
          thumbnail:r.thumbnail,
          media_type:r.media_type || "image",
          spend:0,
          conversions:0,
          clicks:0,
          impressions:0,
          reach:0,
          cpc:0,
          ctr:0
        };
      }
      const a = map[key];
      a.spend += Number(r.spend||0);
      a.conversions += Number(r.conversions||0);
      a.clicks += Number(r.clicks||0);
      a.impressions += Number(r.impressions||0);
      a.reach += Number(r.reach||0);
    });
    return Object.values(map)
      .map(a => ({
        ...a,
        ctr:a.impressions?(a.clicks/a.impressions)*100:Number(a.ctr||0),
        cpc:a.clicks?a.spend/a.clicks:Number(a.cpc||0),
        cost_per_conversion:a.conversions?a.spend/a.conversions:Number(a.cost_per_conversion||0)
      }))
      .filter(a => a.spend > 0 || a.thumbnail)
      .sort((a,b)=>(b.conversions-a.conversions)||(b.spend-a.spend))
      .slice(0,12);
  }

  function score(summary){
    let s=100; if(summary.ctr<1)s-=24; else if(summary.ctr<1.5)s-=14; else if(summary.ctr<2)s-=6; if(summary.cpc>2)s-=18; else if(summary.cpc>1)s-=8; if(summary.cost_per_conversion>50)s-=18; else if(summary.cost_per_conversion>30)s-=8; return Math.max(0,Math.min(100,Math.round(s)));
  }
  const health = s => s>=88?"Excellent":s>=74?"Strong":s>=60?"Stable":"Needs Attention";

  function compareText(current, previous){
    if(!previous) return "";
    const pct = ((current-previous)/previous)*100;
    const up = pct >= 0;
    return `<span class="${up?'up':'down'}">${up?'▲':'▼'} ${Math.abs(pct).toFixed(1)}%</span> vs previous`;
  }

  function updateKpis(summary, previous, compare){
    const map = {
      spend:[fmtEuro(summary.spend),summary.spend,previous.spend],
      conversions:[fmtInt(summary.conversions),summary.conversions,previous.conversions],
      cost_per_conversion:[fmtEuro(summary.cost_per_conversion),summary.cost_per_conversion,previous.cost_per_conversion],
      ctr:[fmtPct(summary.ctr),summary.ctr,previous.ctr],
      cpc:[fmtEuro(summary.cpc),summary.cpc,previous.cpc],
      reach:[fmtInt(summary.reach),summary.reach,previous.reach],
      impressions:[fmtInt(summary.impressions),summary.impressions,previous.impressions],
      clicks:[fmtInt(summary.clicks),summary.clicks,previous.clicks]
    };
    Object.entries(map).forEach(([key,v])=>{
      const card=document.querySelector(`[data-kpi="${key}"]`);
      if(!card)return;
      card.querySelector(".kpi-value").textContent=v[0];
      const c=card.querySelector(".kpi-compare");
      if(c)c.innerHTML=compare?compareText(v[1],v[2]):"";
    });
    document.getElementById("summaryTitle").textContent = `${health(score(summary))} Meta Performance`;
    document.getElementById("summaryText").textContent = `${data.clientName} generated ${fmtInt(summary.conversions)} ${data.conversionName} from ${fmtEuro(summary.spend)} in Meta spend. The average cost per ${data.conversionName.toLowerCase()} was ${fmtEuro(summary.cost_per_conversion)}, with a CTR of ${fmtPct(summary.ctr)}.`;
  }

  function renderTrend(rows, prevRows, compare){
    const ctx=document.getElementById("trendChart"); if(!ctx)return; if(trendChart)trendChart.destroy();
    const datasets=[
      {label:"Spend",data:rows.map(r=>r.spend),borderColor:orange,backgroundColor:"rgba(255,83,13,.12)",tension:.35,fill:true,yAxisID:"y"},
      {label:data.conversionName,data:rows.map(r=>r.conversions),borderColor:black,backgroundColor:"rgba(15,15,15,.08)",tension:.35,fill:false,yAxisID:"y1"}
    ];
    if(compare&&prevRows.length){
      datasets.push({label:"Previous spend",data:prevRows.map(r=>r.spend),borderColor:"#999",borderDash:[6,6],tension:.35,fill:false,yAxisID:"y"});
      datasets.push({label:`Previous ${data.conversionName}`,data:prevRows.map(r=>r.conversions),borderColor:"#bbb",borderDash:[6,6],tension:.35,fill:false,yAxisID:"y1"});
    }
    trendChart=new Chart(ctx,{type:"line",data:{labels:rows.map(r=>r.date),datasets},options:{responsive:true,interaction:{mode:"index",intersect:false},plugins:{legend:{position:"bottom"}},scales:{y:{beginAtZero:true},y1:{beginAtZero:true,position:"right",grid:{drawOnChartArea:false}},x:{grid:{display:false}}}}});
  }

  function renderSpend(campaigns){
    const ctx=document.getElementById("campaignSpendChart"); if(!ctx)return; if(spendChart)spendChart.destroy();
    const top=[...(campaigns||[])].sort((a,b)=>b.spend-a.spend).slice(0,6);
    spendChart=new Chart(ctx,{type:"doughnut",data:{labels:top.map(c=>c.name),datasets:[{data:top.map(c=>c.spend),backgroundColor:[orange,"#111","#ff8b54","#777","#ffc2a8","#ddd"]}]},options:{responsive:true,plugins:{legend:{position:"bottom",labels:{boxWidth:10}}}}});
  }

  function renderCampaigns(campaigns){
    const body=document.getElementById("campaignBody"); if(!body)return;
    body.innerHTML = campaigns.map(c => `<tr><td><strong>${c.name}</strong><small>${c.status||"Active"}</small></td><td>${fmtEuro(c.spend)}</td><td>${fmtInt(c.conversions)}</td><td>${fmtEuro(c.cost_per_conversion)}</td><td>${fmtPct(c.ctr)}</td><td>${fmtEuro(c.cpc)}</td><td>${fmtInt(c.reach)}</td></tr>`).join("");
  }

  function renderCreatives(creatives){
    const grid=document.getElementById("creativeGrid"); if(!grid)return;
    grid.innerHTML = creatives.length ? creatives.map(c => `<article class="creative-card"><div class="creative-thumb">${c.thumbnail?`<img src="${c.thumbnail}" alt="Creative media">`:""}${c.media_type==="video"?`<div class="video-badge">Video</div>`:""}</div><div class="creative-content"><h4>${c.ad_name||""}</h4><div class="metric-row"><span>Spend <strong>${fmtEuro(c.spend)}</strong></span><span>${data.conversionName} <strong>${fmtInt(c.conversions)}</strong></span><span>CTR <strong>${fmtPct(c.ctr)}</strong></span><span>CPC <strong>${fmtEuro(c.cpc)}</strong></span></div></div></article>`).join("") : `<div class="empty-state">No creative previews were returned by Meta for this selected period.</div>`;
  }

  function renderRecommendations(summary, campaigns, creatives){
    const grid=document.getElementById("recommendationGrid"); if(!grid)return;
    const recs=[];
    const best=campaigns[0];
    if(best) recs.push(`Scale the strongest campaign: ${best.name} delivered ${fmtInt(best.conversions)} ${data.conversionName} at ${fmtEuro(best.cost_per_conversion)}.`);
    const costly=campaigns.filter(c=>c.conversions>0).sort((a,b)=>b.cost_per_conversion-a.cost_per_conversion)[0];
    if(costly && costly.cost_per_conversion > summary.cost_per_conversion) recs.push(`Review ${costly.name}; its cost per ${data.conversionName.toLowerCase()} is above the selected-period average.`);
    const topCreative=creatives[0];
    if(topCreative) recs.push(`Use ${topCreative.ad_name} as the creative benchmark; it is currently the strongest ad by selected-period conversions.`);
    if(summary.ctr < 1.5) recs.push("CTR is below benchmark. Prioritise stronger hooks, clearer visual contrast and new opening lines.");
    else recs.push("CTR is healthy. Continue refreshing creative variants to avoid fatigue.");
    if(summary.conversions === 0) recs.push("No conversions were recorded in this period. Confirm tracking, forms and campaign objectives.");
    if(summary.cpc > 1) recs.push("CPC is elevated. Review audience overlap, placement mix and creative relevance.");
    grid.innerHTML = recs.slice(0,4).map(r=>`<div class="recommendation-card"><span>✓</span><p>${r}</p></div>`).join("");
  }

  function refresh(){
    const range=rangeFromSelection();
    const rows=filterRows(data.daily,range.start,range.end);
    const prevRange=previousRange(range.start,range.end);
    const prevRows=filterRows(data.daily,prevRange.start,prevRange.end);
    const campaigns=aggregateCampaigns(filterRows(data.campaignDaily,range.start,range.end));
    const creatives=aggregateCreatives(filterRows(data.creativeDaily || [],range.start,range.end));
    const summary=summarise(rows);
    const previous=summarise(prevRows);
    const compare=document.getElementById("compareToggle").checked;
    document.getElementById("rangeLabel").textContent=range.label;
    const spendLabel = document.getElementById("spendShareLabel");
    if(spendLabel) spendLabel.textContent = `${range.label} by campaign`;
    updateKpis(summary,previous,compare);
    renderTrend(rows,prevRows,compare);
    renderSpend(campaigns);
    renderCampaigns(campaigns);
    renderCreatives(creatives);
    renderRecommendations(summary,campaigns,creatives);
  }

  document.querySelectorAll(".nav-link").forEach(link=>link.addEventListener("click",()=>{document.querySelectorAll(".nav-link").forEach(l=>l.classList.remove("active"));link.classList.add("active");}));
  document.getElementById("campaignSearch")?.addEventListener("input",e=>{const q=e.target.value.toLowerCase();document.querySelectorAll("#campaignTable tbody tr").forEach(row=>{row.style.display=row.innerText.toLowerCase().includes(q)?"":"none";});});
  document.getElementById("dateRange")?.addEventListener("change",refresh);
  document.getElementById("compareToggle")?.addEventListener("change",refresh);
  document.getElementById("customStart")?.addEventListener("change",refresh);
  document.getElementById("customEnd")?.addEventListener("change",refresh);
  refresh();
});
