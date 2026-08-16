import json
import urllib.parse
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler

from lib.engine import (
    fetch_data,
    score_signal,
    ALLOWED_INTERVALS,
    ALLOWED_SYMBOLS,
)

ALLOWED_EXPIRIES = {
    1,
    2,
    3,
    5,
    10,
    15,
}


def send_json(handler, payload, status=200):
    body = json.dumps(
        payload,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    handler.send_response(status)

    handler.send_header(
        "Content-Type",
        "application/json; charset=utf-8"
    )

    handler.send_header(
        "Cache-Control",
        "no-store, max-age=0"
    )

    handler.send_header(
        "Access-Control-Allow-Origin",
        "*"
    )

    handler.send_header(
        "Access-Control-Allow-Methods",
        "GET, OPTIONS"
    )

    handler.send_header(
        "Access-Control-Allow-Headers",
        "Content-Type"
    )

    handler.end_headers()

    handler.wfile.write(body)


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        send_json(
            self,
            {
                "ok": True
            }
        )

    def do_GET(self):

        try:

            # --------------------------------
            # Read URL
            # --------------------------------

            parsed = urllib.parse.urlparse(
                self.path
            )

            query = urllib.parse.parse_qs(
                parsed.query
            )

            # --------------------------------
            # Parameters
            # --------------------------------

            symbol = query.get(
                "symbol",
                ["EUR/USD"]
            )[0]

            interval = query.get(
                "interval",
                ["5min"]
            )[0]

            expiry_raw = query.get(
                "expiry",
                ["5"]
            )[0]

            try:

                expiry = int(
                    expiry_raw
                )

            except ValueError:

                return send_json(
                    self,
                    {
                        "ok": False,
                        "error": "Invalid expiry."
                    },
                    400
                )

            # --------------------------------
            # Validate symbol
            # --------------------------------

            if symbol not in ALLOWED_SYMBOLS:

                return send_json(
                    self,
                    {
                        "ok": False,
                        "error": "Unsupported symbol.",
                        "allowed_symbols": sorted(
                            ALLOWED_SYMBOLS
                        )
                    },
                    400
                )

            # --------------------------------
            # Validate timeframe
            # --------------------------------

            if interval not in ALLOWED_INTERVALS:

                return send_json(
                    self,
                    {
                        "ok": False,
                        "error": "Unsupported interval.",
                        "allowed_intervals": sorted(
                            ALLOWED_INTERVALS
                        )
                    },
                    400
                )

            # --------------------------------
            # Validate expiry
            # --------------------------------

            if expiry not in ALLOWED_EXPIRIES:

                return send_json(
                    self,
                    {
                        "ok": False,
                        "error": "Unsupported expiry.",
                        "allowed_expiries": sorted(
                            ALLOWED_EXPIRIES
                        )
                    },
                    400
                )

            # --------------------------------
            # Fetch market data
            # --------------------------------

            candles = fetch_data(
                symbol,
                interval
            )

            if not candles:

                return send_json(
                    self,
                    {
                        "ok": False,
                        "error": "No market data returned."
                    },
                    502
                )

            if len(candles) < 60:

                return send_json(
                    self,
                    {
                        "ok": False,
                        "error": (
                            "Not enough candles "
                            "for analysis."
                        )
                    },
                    502
                )

            # --------------------------------
            # Generate signal
            # --------------------------------

            (
                signal,
                score,
                reason,
                factors,
                ema9,
                ema21,
                ema50,
            ) = score_signal(
                candles
            )

            # --------------------------------
            # Indicator line formatter
            # --------------------------------

            def line_data(values):

                result = []

                for i, value in enumerate(values):

                    if value is None:
                        continue

                    if i >= len(candles):
                        continue

                    result.append(
                        {
                            "time": candles[i]["time"],
                            "value": value
                        }
                    )

                return result[-140:]

            # --------------------------------
            # Entry / expiry
            # --------------------------------

            now = datetime.now(
                timezone.utc
            )

            expiry_time = (
                now +
                timedelta(
                    minutes=expiry
                )
            )

            # --------------------------------
            # Current price
            # --------------------------------

            price = float(
                candles[-1]["close"]
            )

            decimals = (
                3
                if price >= 10
                else 5
            )

            # --------------------------------
            # Response
            # --------------------------------

            response = {

                "ok": True,

                "symbol": symbol,

                "interval": interval,

                "expiry_minutes": expiry,

                "signal": signal,

                "score": score,

                "reason": reason,

                "entry_time": (
                    now.isoformat()
                ),

                "expiry_time": (
                    expiry_time.isoformat()
                ),

                "price": price,

                "decimals": decimals,

                "candles": candles[-140:],

                "ema9": line_data(
                    ema9
                ),

                "ema21": line_data(
                    ema21
                ),

                "ema50": line_data(
                    ema50
                ),

                "factors": factors,

            }

            return send_json(
                self,
                response,
                200
            )

        # --------------------------------
        # Error handling
        # --------------------------------

        except Exception as exc:

            return send_json(
                self,
                {
                    "ok": False,
                    "error": str(exc)
                },
                502
            )
