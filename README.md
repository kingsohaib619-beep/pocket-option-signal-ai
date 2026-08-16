# Signal AI — Pocket Option Signal Dashboard

Modern black-and-white market analysis dashboard for BUY / SELL / WAIT signals.

## What it does

- Pair selection
- Candle timeframe selection
- Trade expiry selection
- Candlestick chart
- EMA 9 / 21 / 50
- RSI 14
- MACD 12/26/9
- Bollinger Bands context
- ATR volatility filter
- Multi-factor BUY / SELL / WAIT engine
- Confidence score
- Signal countdown
- Local signal history
- API key kept server-side

## Data alignment note

The application uses one configured market-data source for both the chart and the signal engine, which avoids calculating a signal from one source and displaying another. It does **not** guarantee tick-for-tick equality with Pocket Option because the platform may use a different pricing feed or candle construction. Validate the live feed against your Pocket Option chart before real-money use.

## Local setup

1. Install Python 3.11+.
2. Set `TWELVE_DATA_API_KEY`.
3. Run the static frontend with any local HTTP server and expose `/api` through Vercel CLI, or deploy directly to Vercel.

## Vercel deployment

1. Push this folder to GitHub.
2. Import the repository into Vercel.
3. In Vercel Project Settings → Environment Variables, add:
   - Name: `TWELVE_DATA_API_KEY`
   - Value: your Twelve Data key
   - Environments: Production, Preview, Development as needed.
4. Redeploy.
5. Open `/api/signal?symbol=EUR%2FUSD&interval=5min&expiry=5` to test the API.

## Important

This is an analysis tool, not an auto-trading bot and not a profit guarantee. The score is a model confidence score, not a statistical probability of winning a trade. Backtest and forward-test before risking money.
