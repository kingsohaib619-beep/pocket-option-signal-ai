from signal import fetch_data, score_signal, ALLOWED_INTERVALS, ALLOWED_SYMBOLS
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs, urlparse
import json

def response(body, status=200):
    return (json.dumps(body), status, {"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"})

def handler(request):
    # Works with Vercel's Python function request object.
    query = getattr(request, "query", None) or {}
    if not query:
        path = getattr(request, "url", "")
        query = {k:v[-1] for k,v in parse_qs(urlparse(path).query).items()}
    symbol=query.get("symbol","EUR/USD")
    interval=query.get("interval","5min")
    expiry=int(query.get("expiry","5"))
    if symbol not in ALLOWED_SYMBOLS: return response({"error":"Unsupported symbol"},400)
    if interval not in ALLOWED_INTERVALS: return response({"error":"Unsupported interval"},400)
    if expiry not in {1,2,3,5,10,15}: return response({"error":"Unsupported expiry"},400)
    try:
        candles=fetch_data(symbol,interval)
        if len(candles)<60: raise RuntimeError("Not enough candles for analysis.")
        signal,score,reason,factors,e9,e21,e50=score_signal(candles)
        clean=lambda arr:[{"time":candles[i]["time"],"value":v} for i,v in enumerate(arr) if v is not None]
        entry=datetime.now(timezone.utc)
        expiry_time=entry+timedelta(minutes=expiry)
        price=candles[-1]["close"]
        decimals=3 if price>10 else 5
        return response({
            "symbol":symbol,"interval":interval,"expiry_minutes":expiry,
            "signal":signal,"score":score,"reason":reason,
            "entry_time":entry.isoformat(),"expiry_time":expiry_time.isoformat(),
            "price":price,"decimals":decimals,"candles":candles[-140:],
            "ema9":clean(e9)[-140:],"ema21":clean(e21)[-140:],"ema50":clean(e50)[-140:],
            "factors":factors
        })
    except Exception as e:
        return response({"error":str(e)},502)

# Vercel Python runtime accepts an exported handler.
