# Tickwatch for Vercel

Static dashboard (`public/index.html`) + one Python serverless function (`api/quotes.py`).
The browser polls `/api/quotes` every 10 s, keeps its own price history, and runs the alerts itself.
Your price alerts are saved in your browser (localStorage), so every visitor has their own.

## Deploy from GitHub (easiest)
1. Push this folder to a GitHub repo.
2. vercel.com > Add New > Project > import the repo. No build settings needed.
3. Project Settings > Environment Variables: add `FINNHUB_API_KEY` (free key from finnhub.io). Optional: `SYMBOLS`.
4. Redeploy. Without a key the site still works on simulated prices.

## Deploy from the command line
    npm i -g vercel
    vercel                # first deploy, answer the prompts
    vercel env add FINNHUB_API_KEY
    vercel --prod

## Run locally
    vercel dev            # http://localhost:3000, reads .env
(Opening index.html directly will not work because /api/quotes needs the function.)

## Limits
- History starts when the tab opens (no server memory). Alerts only run while a tab is open.
- Free Finnhub tier: 60 calls/min. 8 symbols with 10 s caching uses about 48/min however many people visit.
- Quotes may be delayed. Not financial advice.
