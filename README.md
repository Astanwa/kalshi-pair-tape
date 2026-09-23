# Kalshi BTC 15m pair tape (paper)

Live forward test of a two-sided resting-bid strategy on Kalshi's `KXBTC15M` markets: every 15-minute window, rest **buy YES at 0.40** and **buy NO at 0.40** (25 contracts per leg). If both fill, the position nets flat and pays 0.20 per contract. If only one fills, that leg is held to settlement.

Three ledgers run side by side:

- **Trade-tape fills, all day** (`btc15pairT`, from 2026-09-22): a leg counts as filled once at least 25 contracts have *printed* at or below 0.40 on that side (Kalshi public trade tape, polled every 20 s). A seller at ≤ 0.40 cannot coexist with a resting 0.40 bid, so prints are direct fill evidence; volume proxies queue position.
- **Trade-tape fills, 00-03 ET only** (`btc15pairN`): same model, posts only in windows starting 00:00-02:45 ET (the one time block that paired >70% in both halves of the Sep 16-22 backtest).
- **Quote-touch fills** (`btc15pair`, from 2026-09-13): the original, fills only when the best ask touches 0.40. Calibrated against the tape it undercounts real fills badly (47.6% vs 64.3% paired on the same windows), kept as a control.

- Dashboard: `index.html` (GitHub Pages) — auto-refreshes.
- `data/<ledger>.csv|json` — one row per window per ledger. `outcome`: `both`, `yes_only`, `no_only`, `none`. `pnl` in dollars. `yes_vol`/`no_vol`: contracts printed at/below 0.40 on each side since posting (tape ledgers).
- `data/quotes.csv` — the YES bid/ask path (~40 s samples) for every window on the tape.
- `data/summary.json` — totals and per-day rollup.

Updated every 5 minutes from the trading database. Started 2026-09-13 22:10 UTC. Paper money only.
