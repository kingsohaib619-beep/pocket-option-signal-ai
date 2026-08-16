import os
import json
import urllib.parse
from datetime import datetime, timezone, timedelta

from lib.engine import (
    fetch_data,
    score_signal,
    ALLOWED_INTERVALS,
    ALLOWED_SYMBOLS,
)

ALLOWED_EXPIRIES = {1, 2, 3, 5, 10, 15}


def response(body, status=200):
    return (
        json.dumps(body, separators=(",", ":")),
        status,
        {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store, max-age=0",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
    )


def handler(request):
    try:
        query = getattr(request, "query", None) or {}

        if not query:
            url = getattr(request, "url", "") or ""
            parsed = urllib.parse.urlparse(url)
            parsed_query = urllib.parse.parse_qs(parsed.query)
            query = {
                key: values[-1]
                for key, values in parsed_query.items()
            }

        symbol = query.get("symbol", "EUR/USD")
        interval = query.get("interval", "5min")

        try:
            expiry = int(query.get("expiry", "5"))
        except (TypeError, ValueError):
            return response(
                {"error": "Invalid expiry."},
                400
            )

        if symbol not in ALLOWED_SYMBOLS:
            return response(
                {"error": "Unsupported symbol."},
                400
            )

        if interval not in ALLOWED_INTERVALS:
            return response(
                {"error": "Unsupported interval."},
                400
            )

        if expiry not in ALLOWED_EXPIRIES:
            return response(
                {"error": "Unsupported expiry."},
                400
            )

        candles = fetch_data(symbol, interval)

        if len(candles) < 60:
            return response(
                {"error": "Not enough candles for analysis."},
                502
            )

        (
            signal,
            score,
            reason,
            factors,
            ema9,
            ema21,
            ema50,
        ) = score_signal(candles)

        def line_data(values):
            return [
                {
                    "time": candles[i]["time"],
                    "value": value,
                }
                for i, value in enumerate(values)
                if value is not None
            ][-140:]

        entry_time = datetime.now(timezone.utc)
        expiry_time = entry_time + timedelta(minutes=expiry)

        price = candles[-1]["close"]

        decimals = 3 if price > 10 else 5

        return response({
            "ok": True,

            "symbol": symbol,
            "interval": interval,
            "expiry_minutes": expiry,

            "signal": signal,
            "score": score,
            "reason": reason,

            "entry_time": entry_time.isoformat(),
            "expiry_time": expiry_time.isoformat(),

            "price": price,
            "decimals": decimals,

            "candles": candles[-140:],

            "ema9": line_data(ema9),
            "ema21": line_data(ema21),
            "ema50": line_data(ema50),

            "factors": factors,
        })

    except Exception as exc:
        return response(
            {
                "ok": False,
                "error": str(exc),
            },
            502,
        )
