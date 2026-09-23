#!/usr/bin/env python3
"""Export the Kalshi BTC-15m pair paper tapes (3 ledgers) to CSV/JSON and push if changed. Cron every 5 min."""
import csv, hashlib, json, os, sqlite3, subprocess, datetime as dt
from zoneinfo import ZoneInfo
DB = "/Users/abot1/openclaw_sandbox/trading/data/trading.db"
HERE = os.path.dirname(os.path.abspath(__file__)); ET = ZoneInfo("America/New_York")
LEDGERS = [("btc15pairT", "Trade-tape fills, all day", "fills when trades print at/below 0.40 (>=25 contracts) on the public tape; started 2026-09-22 20:36 ET"),
           ("btc15pairN", "Trade-tape fills, 00-03 ET only", "same fill model, posts only in windows starting 00:00-02:45 ET; started 2026-09-22"),
           ("btc15pair", "Quote-touch fills (original)", "fills only when the best ask touches 0.40 — undercounts real fills (calibrated 47.6% vs 64.3% paired on the tape); started 2026-09-13")]
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.row_factory = sqlite3.Row
cols = ["window_ts", "window_et", "window_utc", "ticker", "level", "contracts", "mid_at_post", "yes_status", "no_status",
        "yes_filled_at", "no_filled_at", "yes_vol", "no_vol", "outcome", "result", "pnl", "status", "placed_at", "settled_at"]
summary = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "level": 0.40, "contracts_per_leg": 25, "strategies": {}}
digest = hashlib.sha1()
for ledger, label, note in LEDGERS:
    try:
        bets = [dict(r) for r in con.execute(f"SELECT * FROM {ledger}_bets ORDER BY window_ts")]
        acct = con.execute(f"SELECT cash, start_cash FROM {ledger}_account WHERE id=1").fetchone()
    except sqlite3.OperationalError:
        continue
    for b in bets:
        b["window_et"] = dt.datetime.fromtimestamp(b["window_ts"], ET).strftime("%Y-%m-%d %H:%M")
        b["window_utc"] = dt.datetime.fromtimestamp(b["window_ts"], dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
        for k in ("yes_vol", "no_vol"): b[k] = round(b.get(k) or 0)
    rows = [{k: b.get(k) for k in cols} for b in bets]
    with open(f"{HERE}/data/{ledger}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    json.dump(rows, open(f"{HERE}/data/{ledger}.json", "w"), indent=0)
    digest.update(json.dumps(rows).encode())
    settled = [b for b in bets if b["status"] == "settled"]
    both = sum(b["outcome"] == "both" for b in settled); single = sum(b["outcome"] in ("yes_only", "no_only") for b in settled)
    single_won = sum(b["outcome"] in ("yes_only", "no_only") and (b["pnl"] or 0) > 0 for b in settled); none = sum(b["outcome"] == "none" for b in settled)
    by_day = {}
    for b in settled:
        d = b["window_et"][:10]; x = by_day.setdefault(d, {"day": d, "n": 0, "both": 0, "single": 0, "none": 0, "pnl": 0.0})
        x["n"] += 1; x["both" if b["outcome"] == "both" else "single" if b["outcome"] in ("yes_only", "no_only") else "none"] += 1; x["pnl"] += b["pnl"] or 0
    summary["strategies"][ledger] = {"label": label, "note": note, "rows_file": f"data/{ledger}.json", "start_cash": acct["start_cash"] if acct else None,
        "cash": round(acct["cash"], 2) if acct else None, "windows_settled": len(settled), "both": both, "single": single, "single_won": single_won, "none": none,
        "both_rate_of_filled": round(both / max(1, both + single), 4), "pnl": round(sum(b["pnl"] or 0 for b in settled), 2), "open_windows": len(bets) - len(settled),
        "by_day": sorted(by_day.values(), key=lambda x: x["day"])}
# quotes for all pair windows (union)
wins = sorted({r["window_ts"] for s in summary["strategies"] for r in json.load(open(f"{HERE}/data/{s}.json"))}) or [0]
q = con.execute(f"SELECT window_ts, secs_in, yes_bid, yes_ask FROM btc15_bbo_log WHERE window_ts IN ({','.join('?'*len(wins))}) ORDER BY window_ts, secs_in", wins).fetchall()
with open(f"{HERE}/data/quotes.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["window_ts", "secs_in", "yes_bid", "yes_ask"]); w.writerows([tuple(r) for r in q])
hp = f"{HERE}/.last_hash"; d = digest.hexdigest()
if os.path.exists(hp) and open(hp).read().strip() == d:
    print(summary["generated_at"], "no change"); raise SystemExit(0)
open(hp, "w").write(d); json.dump(summary, open(f"{HERE}/data/summary.json", "w"), indent=1)
env = {**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}
def git(*a): return subprocess.run(["git", *a], cwd=HERE, env=env, capture_output=True, text=True)
if git("status", "--porcelain").stdout.strip():
    git("add", "-A"); git("commit", "-q", "-m", f"tape update {summary['generated_at']}")
    r = git("push", "-q"); print(summary["generated_at"], "pushed" if r.returncode == 0 else f"push failed: {r.stderr.strip()[:200]}")
