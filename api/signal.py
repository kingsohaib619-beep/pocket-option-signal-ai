import os, math, urllib.parse, urllib.request, json
from datetime import datetime, timezone, timedelta
from statistics import mean

API_KEY = os.getenv("TWELVE_DATA_API_KEY")
BASE = "https://api.twelvedata.com/time_series"
ALLOWED_INTERVALS = {"1min","5min","15min","30min","1h"}
ALLOWED_SYMBOLS = {
    "EUR/USD","GBP/USD","USD/JPY","USD/CHF","AUD/USD","USD/CAD","NZD/USD",
    "EUR/GBP","EUR/JPY","GBP/JPY"
}

def fetch_data(symbol, interval):
    if not API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY is not configured in Vercel.")
    params = urllib.parse.urlencode({
        "symbol": symbol, "interval": interval, "outputsize": 180,
        "timezone": "UTC", "apikey": API_KEY
    })
    req = urllib.request.Request(BASE+"?"+params, headers={"User-Agent":"SignalAI/1.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        data=json.loads(r.read().decode())
    if data.get("status")=="error" or "values" not in data:
        raise RuntimeError(data.get("message","Market data provider error"))
    vals=list(reversed(data["values"]))
    candles=[]
    for x in vals:
        candles.append({
            "time": int(datetime.fromisoformat(x["datetime"].replace("Z","+00:00")).timestamp()),
            "open":float(x["open"]),"high":float(x["high"]),
            "low":float(x["low"]),"close":float(x["close"])
        })
    return candles

def ema(values, period):
    if len(values)<period: return [None]*len(values)
    out=[None]*len(values); k=2/(period+1); prev=sum(values[:period])/period
    out[period-1]=prev
    for i in range(period,len(values)):
        prev=values[i]*k+prev*(1-k); out[i]=prev
    return out

def rsi(values, period=14):
    out=[None]*len(values)
    if len(values)<=period:return out
    gains=[]; losses=[]
    for i in range(1,len(values)):
        d=values[i]-values[i-1]; gains.append(max(d,0)); losses.append(max(-d,0))
    ag=sum(gains[:period])/period; al=sum(losses[:period])/period
    out[period]=100 if al==0 else 100-(100/(1+ag/al))
    for i in range(period+1,len(values)):
        ag=(ag*(period-1)+gains[i-1])/period; al=(al*(period-1)+losses[i-1])/period
        out[i]=100 if al==0 else 100-(100/(1+ag/al))
    return out

def macd(values):
    e12=ema(values,12); e26=ema(values,26)
    line=[None if e12[i] is None or e26[i] is None else e12[i]-e26[i] for i in range(len(values))]
    clean=[x for x in line if x is not None]
    sigclean=ema(clean,9)
    signal=[None]*len(values); j=0
    for i,x in enumerate(line):
        if x is not None:
            signal[i]=sigclean[j]; j+=1
    return line,signal

def bollinger(values, period=20, mult=2):
    mid=[None]*len(values); upper=[None]*len(values); lower=[None]*len(values)
    for i in range(period-1,len(values)):
        w=values[i-period+1:i+1]; m=mean(w); sd=math.sqrt(sum((x-m)**2 for x in w)/period)
        mid[i]=m; upper[i]=m+mult*sd; lower[i]=m-mult*sd
    return mid,upper,lower

def atr(candles, period=14):
    tr=[]
    for i,c in enumerate(candles):
        if i==0: tr.append(c["high"]-c["low"])
        else: tr.append(max(c["high"]-c["low"],abs(c["high"]-candles[i-1]["close"]),abs(c["low"]-candles[i-1]["close"])))
    return ema(tr,period)

def score_signal(c):
    closes=[x["close"] for x in c]
    e9,e21,e50=ema(closes,9),ema(closes,21),ema(closes,50)
    rv=rsi(closes); ml,ms=macd(closes); bm,bu,bl=bollinger(closes); av=atr(c)
    i=len(c)-1
    # Use the last completed candle when possible. This reduces intrabar repainting.
    j=i-1 if i>50 else i
    points=0; max_points=10; factors=[]
    def factor(name, state, value):
        factors.append({"name":name,"state":state,"value":value})
    # Trend structure: 3 points
    if e9[j] and e21[j] and e50[j]:
        if e9[j]>e21[j]>e50[j]: points+=3; factor("Trend","positive","Bullish")
        elif e9[j]<e21[j]<e50[j]: points-=3; factor("Trend","negative","Bearish")
        else: factor("Trend","neutral","Mixed")
    # Momentum: RSI + MACD = 3 points
    if rv[j] is not None:
        if 52<=rv[j]<=68: points+=1; factor("RSI","positive",f"{rv[j]:.1f} Bullish")
        elif 32<=rv[j]<=48: points-=1; factor("RSI","negative",f"{rv[j]:.1f} Bearish")
        elif rv[j]>72: factor("RSI","neutral",f"{rv[j]:.1f} Overbought")
        elif rv[j]<28: factor("RSI","neutral",f"{rv[j]:.1f} Oversold")
        else: factor("RSI","neutral",f"{rv[j]:.1f} Neutral")
    if ml[j] is not None and ms[j] is not None:
        if ml[j]>ms[j]: points+=2; factor("MACD","positive","Bullish")
        else: points-=2; factor("MACD","negative","Bearish")
    # Bollinger context: 2 points
    if bu[j] and bl[j]:
        pos=(closes[j]-bl[j])/(bu[j]-bl[j]) if bu[j]!=bl[j] else .5
        if pos<.18: points+=1; factor("Bollinger","positive","Lower zone")
        elif pos>.82: points-=1; factor("Bollinger","negative","Upper zone")
        else: factor("Bollinger","neutral","Mid zone")
    # Price action: 2 points
    body=closes[j]-c[j]["open"]; rng=max(c[j]["high"]-c[j]["low"],1e-12)
    if body/rng>.35: points+=1; factor("Price action","positive","Bullish body")
    elif body/rng<-.35: points-=1; factor("Price action","negative","Bearish body")
    else: factor("Price action","neutral","Indecisive")
    if av[j] is not None:
        recent=[x["high"]-x["low"] for x in c[max(0,j-9):j+1]]
        ratio=(av[j]/mean(recent)) if recent else 1
        if .65<=ratio<=1.8: factor("Volatility","positive","Tradable")
        else: factor("Volatility","neutral","Extreme/low")
    # Score maps directional evidence to 0..100, with a conservative WAIT gate.
    raw=50+(points/10)*50
    if points>=6: signal="BUY"
    elif points<=-6: signal="SELL"
    else: signal="WAIT"
    confidence=round(min(99,max(1,abs(raw-50)*1.0+50 if signal!="WAIT" else 50-abs(points)*3)))
    if signal=="BUY": reason="Bullish trend and momentum confirmations align."
    elif signal=="SELL": reason="Bearish trend and momentum confirmations align."
    else: reason="Signals are mixed; the engine refuses to force an entry."
    return signal,confidence,reason,factors,e9,e21,e50

def handler(request):
    # Vercel Python request compatibility is handled by the adapter below.
    pass

def api_response(body,status=200):
    return body,status

# Flask is intentionally not required; Vercel supports a simple Python function
# with the request/response adapter in api/index.py.
