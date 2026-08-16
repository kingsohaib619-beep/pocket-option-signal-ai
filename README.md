# Pocket Option Signal AI

Vercel-ready market-signal dashboard.

## Important routing fix
The frontend calls `/api/signal`, so the public Vercel function is `api/signal.py`.
The indicator/data engine is `api/engine.py`.
There is intentionally no `vercel.json`; Vercel automatically detects Python files inside `api/`.

## Deploy
1. Push all files to GitHub.
2. Import the repository into Vercel.
3. Add `TWELVE_DATA_API_KEY` in Vercel Project Settings → Environment Variables.
4. Redeploy.
5. Test:
   `/api/signal?symbol=EUR%2FUSD&interval=5min&expiry=5`

The chart and signal engine use the same market-data provider. This does not guarantee tick-for-tick equality with Pocket Option, because different feeds can construct candles differently. Test on demo before risking money.
