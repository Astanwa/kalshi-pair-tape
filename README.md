# Kalshi BTC 15m pair tape (paper)

Live forward test of a two-sided resting-bid strategy on Kalshi's `KXBTC15M` markets: every 15-minute window, rest **buy YES at 0.40** and **buy NO at 0.40** (25 contracts per leg). If both fill, the position nets flat and pays 0.20 per contract. If only one fills, that leg is held to settlement.

Fills are simulated from the live Kalshi order book every 20 seconds: a leg counts as filled when the market quote reaches our level (YES ask ≤ 0.40 / NO ask ≤ 0.40). That is an optimistic upper bound — real queue position can delay fills.

- Dashboard: `index.html` (GitHub Pages) — auto-refreshes.
- `data/pair_bets.csv|json` — one row per window. `outcome`: `both`, `yes_only`, `no_only`, `none`. `pnl` in dollars.
- `data/quotes.csv` — the YES bid/ask path (~40 s samples) for every window on the tape.
- `data/summary.json` — totals and per-day rollup.

Updated every 5 minutes from the trading database. Started 2026-09-13 22:10 UTC. Paper money only.
