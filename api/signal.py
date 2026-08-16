import json
import os
import urllib.parse
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler

from engine import (
    fetch_data,
    score_signal,
    ALLOWED_INTERVALS,
    ALLOWED_SYMBOLS,
)

ALLOWED_EXPIRIES = {1, 2, 3, 5, 10, 15}


def send_json(handler, payload, status=200):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store, max-age=0")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_json(self, {"ok": True})

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(parsed.query)

            symbol = q.get("symbol", ["EUR/USD"])[0]
            interval = q.get("interval", ["5min"])[0]
            expiry = int(q.get("expiry", ["5"])[0])

            if symbol not in ALLOWED_SYMBOLS:
                return send_json(self, {"error": "Unsupported symbol."}, 400)
            if interval not in ALLOWED_INTERVALS:
                return send_json(self, {"error": "Unsupported interval."}, 400)
            if expiry not in ALLOWED_EXPIRIES:
                return send_json(self, {"error": "Unsupported expiry."}, 400)

            candles = fetch_data(symbol, interval)
            if len(candles) < 60:
                raise RuntimeError("Not enough candles for analysis.")

            signal, score, reason, factors, e9, e21, e50 = score_signal(candles)

            def line_data(values):
                return [
                    {"time": candles[i]["time"], "value": value}
                    for i, value in enumerate(values)
                    if value is not None
                ][-140:]

            entry = datetime.now(timezone.utc)
            expiry_time = entry + timedelta(minutes=expiry)
            price = candles[-1]["close"]
            decimals = 3 if price > 10 else 5

            return send_json(self, {
                "symbol": symbol,
                "interval": interval,
                "expiry_minutes": expiry,
                "signal": signal,
                "score": score,
                "reason": reason,
                "entry_time": entry.isoformat(),
                "expiry_time": expiry_time.isoformat(),
                "price": price,
                "decimals": decimals,
                "candles": candles[-140:],
                "ema9": line_data(e9),
                "ema21": line_data(e21),
                "ema50": line_data(e50),
                "factors": factors,
            })
        except Exception as exc:
            return send_json(self, {"error": str(exc)}, 502)
