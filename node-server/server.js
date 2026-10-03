// Tickwatch server: fetches quotes (Finnhub, or a simulator) and streams them to the browser via SSE.
const http = require('http'), fs = require('fs'), path = require('path');

const envFile = path.join(__dirname, '.env');
if (fs.existsSync(envFile)) for (const l of fs.readFileSync(envFile, 'utf8').split('\n')) {
  const m = l.match(/^\s*([A-Z_]+)\s*=\s*(.*?)\s*$/);
  if (m && !(m[1] in process.env)) process.env[m[1]] = m[2];
}
const KEY = process.env.FINNHUB_API_KEY || '';
const SYMBOLS = (process.env.SYMBOLS || 'AAPL,MSFT,NVDA,TSLA,AMZN,GOOGL,META,AMD')
  .split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
const PORT = +process.env.PORT || 3000;
const POLL = Math.max(+process.env.POLL_MS || 10000, 2000);
const MAXH = 420;

const history = Object.fromEntries(SYMBOLS.map(s => [s, []]));
const open = {};
const clients = new Set();

function push(prices) {
  const out = {};
  for (const [s, p] of Object.entries(prices)) {
    if (!(p > 0)) continue;
    const h = history[s]; h.push(p); if (h.length > MAXH) h.shift();
    out[s] = p;
  }
  if (Object.keys(out).length) {
    const msg = `event: tick\ndata: ${JSON.stringify(out)}\n\n`;
    for (const c of clients) c.write(msg);
  }
}

async function poll() {
  const res = await Promise.all(SYMBOLS.map(async s => {
    try {
      const r = await fetch(`https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(s)}&token=${KEY}`);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const q = await r.json();
      if (open[s] == null && q.o > 0) open[s] = q.o;
      return [s, q.c];
    } catch (e) { console.warn(`${s}: fetch failed (${e.message})`); return [s, 0]; }
  }));
  push(Object.fromEntries(res));
}

function startSim() {
  const g = () => { let u = 0, v = 0; while (!u) u = Math.random(); while (!v) v = Math.random(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  const st = {};
  for (const s of SYMBOLS) {
    let h = 0; for (const ch of s) h = (h * 31 + ch.charCodeAt(0)) % 997;
    st[s] = { p: 20 + h % 380, d: 0, v: .0008 + (h % 10) * .0001 };
  }
  const tick = () => { const o = {}; for (const s of SYMBOLS) { const x = st[s]; x.d = x.d * .985 + g() * x.v * .35; x.p = Math.max(1, x.p * (1 + x.d + g() * x.v)); o[s] = +x.p.toFixed(2); } return o; };
  for (let i = 0; i < 200; i++) for (const [s, p] of Object.entries(tick())) history[s].push(p);
  for (const s of SYMBOLS) open[s] = history[s][0];
  setInterval(() => push(tick()), 1000);
}

const server = http.createServer((req, res) => {
  if (req.url === '/stream') {
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
    const init = {
      symbols: SYMBOLS,
      history: Object.fromEntries(SYMBOLS.map(s => [s, history[s]])),
      open: Object.fromEntries(SYMBOLS.map(s => [s, open[s] ?? history[s][0]])),
      mode: KEY ? 'live' : 'simulated',
      pollMs: KEY ? POLL : 1000
    };
    res.write(`event: init\ndata: ${JSON.stringify(init)}\n\n`);
    clients.add(res);
    req.on('close', () => clients.delete(res));
    return;
  }
  if (req.url === '/' || req.url === '/index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    fs.createReadStream(path.join(__dirname, 'public', 'index.html')).pipe(res);
    return;
  }
  res.writeHead(404); res.end('Not found');
});
setInterval(() => { for (const c of clients) c.write(':hb\n\n'); }, 25000);

(async () => {
  if (KEY) {
    await poll();
    for (const s of [...SYMBOLS]) if (!history[s].length) { console.warn(`No data for ${s}, dropping it`); SYMBOLS.splice(SYMBOLS.indexOf(s), 1); }
    if (!SYMBOLS.length) { console.error('No valid symbols. Check SYMBOLS and FINNHUB_API_KEY.'); process.exit(1); }
    setInterval(poll, POLL);
  } else startSim();
  server.listen(PORT, () => console.log(`Tickwatch running at http://localhost:${PORT} (${KEY ? 'live Finnhub quotes' : 'simulated prices'})`));
})();
