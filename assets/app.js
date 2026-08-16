let chart, candleSeries, ema9Series, ema21Series, ema50Series, refreshTimer, countdownTimer;
const $ = id => document.getElementById(id);
const state = { lastSignal:null, lastExpiryMs:null };

function initChart(){
  const el = $("chart");
  chart = LightweightCharts.createChart(el,{
    layout:{background:{color:"#ffffff"},textColor:"#777"},
    grid:{vertLines:{color:"#f1f1ee"},horzLines:{color:"#f1f1ee"}},
    rightPriceScale:{borderColor:"#eee"},
    timeScale:{borderColor:"#eee",timeVisible:true,secondsVisible:false},
    crosshair:{mode:1},
    width:el.clientWidth,height:el.clientHeight
  });
  candleSeries=chart.addCandlestickSeries({upColor:"#111",downColor:"#999",borderVisible:false,wickUpColor:"#111",wickDownColor:"#999"});
  ema9Series=chart.addLineSeries({color:"#111",lineWidth:1.5});
  ema21Series=chart.addLineSeries({color:"#777",lineWidth:1.2});
  ema50Series=chart.addLineSeries({color:"#bbb",lineWidth:1.1});
  new ResizeObserver(()=>chart.applyOptions({width:el.clientWidth,height:el.clientHeight})).observe(el);
}
function fmtTime(s){return new Date(s).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"});}
function renderFactors(factors){
  $("factors").innerHTML = factors.map(f=>{
    const cls=f.state==="positive"?"ok":f.state==="negative"?"bad":"neutral";
    const icon=f.state==="positive"?"✓":f.state==="negative"?"×":"•";
    return `<div class="factor"><span>${f.name}</span><span class="value ${cls}">${icon} ${f.value}</span></div>`;
  }).join("");
}
function updateSignal(data){
  const s=data.signal;
  const card=$("signalCard");
  card.classList.remove("signal-buy","signal-sell","signal-wait");
  card.classList.add(`signal-${s.toLowerCase()}`);
  $("signalIcon").textContent=s==="BUY"?"↑":s==="SELL"?"↓":"—";
  $("signalLabel").textContent=s;
  $("signalReason").textContent=data.reason;
  $("confidenceBadge").textContent=`${data.score}/100`;
  $("scoreValue").textContent=`${data.score}/100`;
  $("scoreBar").style.width=`${data.score}%`;
  $("entryTime").textContent=fmtTime(data.entry_time);
  $("expiryTime").textContent=fmtTime(data.expiry_time);
  $("entryPrice").textContent=data.price.toFixed(data.decimals);
  renderFactors(data.factors);
  state.lastSignal=data;
  state.lastExpiryMs=new Date(data.expiry_time).getTime();
  clearInterval(countdownTimer);
  countdownTimer=setInterval(()=>{
    const left=Math.max(0,state.lastExpiryMs-Date.now());
    const sec=Math.floor(left/1000);
    $("countdown").textContent=`${Math.floor(sec/60)}:${String(sec%60).padStart(2,"0")}`;
    if(left<=0) clearInterval(countdownTimer);
  },250);
  saveHistory(data);
}
function renderHistory(){
  const rows=JSON.parse(localStorage.getItem("signalHistory")||"[]");
  $("historyBody").innerHTML=rows.length?rows.map(r=>`<tr><td>${r.time}</td><td>${r.symbol}</td><td>${r.tf}</td><td><b>${r.signal}</b></td><td>${r.score}</td><td>${r.expiry}m</td></tr>`).join(""):`<tr><td colspan="6" class="empty">No signals yet.</td></tr>`;
}
function saveHistory(data){
  const rows=JSON.parse(localStorage.getItem("signalHistory")||"[]");
  rows.unshift({time:fmtTime(data.entry_time),symbol:data.symbol,tf:data.interval,signal:data.signal,score:data.score,expiry:data.expiry_minutes});
  localStorage.setItem("signalHistory",JSON.stringify(rows.slice(0,20))); renderHistory();
}
async function analyze(){
  const symbol=$("symbol").value, interval=$("interval").value, expiry=Number($("expiry").value);
  $("analyzeBtn").disabled=true; $("analyzeBtn").textContent="Analyzing…";
  $("statusText").textContent="Fetching market data";
  $("chartTitle").textContent=`${symbol} · ${interval.replace("min","M").replace("1h","1H")}`;
  try{
    const res=await fetch(`/api/signal?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&expiry=${expiry}`,{cache:"no-store"});
    const data=await res.json();
    if(!res.ok) throw new Error(data.error||"Market data request failed");
    candleSeries.setData(data.candles);
    ema9Series.setData(data.ema9); ema21Series.setData(data.ema21); ema50Series.setData(data.ema50);
    chart.timeScale().fitContent();
    updateSignal(data);
    $("statusText").textContent="Analysis updated";
    $("chartError").classList.add("hidden");
  }catch(e){
    $("statusText").textContent="Error";
    $("chartError").textContent=e.message;
    $("chartError").classList.remove("hidden");
  }finally{
    $("analyzeBtn").disabled=false; $("analyzeBtn").innerHTML='Analyze market <span>→</span>';
  }
}
$("analyzeBtn").addEventListener("click",analyze);
$("clearHistory").addEventListener("click",()=>{localStorage.removeItem("signalHistory");renderHistory();});
$("interval").addEventListener("change",()=>{ $("chartTitle").textContent=`${$("symbol").value} · ${$("interval").value}`; });
$("symbol").addEventListener("change",()=>{ $("chartTitle").textContent=`${$("symbol").value} · ${$("interval").value}`; });
window.addEventListener("load",()=>{initChart();renderHistory();analyze();});
