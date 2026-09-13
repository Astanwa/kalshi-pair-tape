#!/usr/bin/env python3
"""Export the Kalshi BTC-15m pair paper tape to CSV/JSON and push if changed. Cron every 5 min."""
import csv, json, os, sqlite3, subprocess, datetime as dt
from zoneinfo import ZoneInfo
DB = "/Users/abot1/openclaw_sandbox/trading/data/trading.db"
HERE = os.path.dirname(os.path.abspath(__file__)); ET = ZoneInfo("America/New_York")
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.row_factory = sqlite3.Row
bets = [dict(r) for r in con.execute("SELECT * FROM btc15pair_bets ORDER BY window_ts")]
acct = con.execute("SELECT cash, start_cash FROM btc15pair_account WHERE id=1").fetchone()
for b in bets:
    b["window_et"] = dt.datetime.fromtimestamp(b["window_ts"], ET).strftime("%Y-%m-%d %H:%M")
    b["window_utc"] = dt.datetime.fromtimestamp(b["window_ts"], dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
cols = ["window_ts", "window_et", "window_utc", "ticker", "level", "contracts", "mid_at_post", "yes_status", "no_status",
        "yes_filled_at", "no_filled_at", "outcome", "result", "pnl", "status", "placed_at", "settled_at"]
with open(f"{HERE}/data/pair_bets.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(bets)
json.dump([{k: b.get(k) for k in cols} for b in bets], open(f"{HERE}/data/pair_bets.json", "w"), indent=0)
wins = tuple(b["window_ts"] for b in bets) or (0,)
q = con.execute(f"SELECT window_ts, secs_in, yes_bid, yes_ask FROM btc15_bbo_log WHERE window_ts IN ({','.join('?'*len(wins))}) ORDER BY window_ts, secs_in", wins).fetchall()
with open(f"{HERE}/data/quotes.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["window_ts", "secs_in", "yes_bid", "yes_ask"]); w.writerows([tuple(r) for r in q])
settled = [b for b in bets if b["status"] == "settled"]
both = sum(b["outcome"] == "both" for b in settled); single = sum(b["outcome"] in ("yes_only", "no_only") for b in settled)
single_won = sum(b["outcome"] in ("yes_only", "no_only") and (b["pnl"] or 0) > 0 for b in settled); none = sum(b["outcome"] == "none" for b in settled)
by_day = {}
for b in settled:
    d = b["window_et"][:10]; x = by_day.setdefault(d, {"day": d, "n": 0, "both": 0, "single": 0, "none": 0, "pnl": 0.0})
    x["n"] += 1; x[("both" if b["outcome"] == "both" else "single" if b["outcome"] in ("yes_only", "no_only") else "none")] += 1; x["pnl"] += b["pnl"] or 0
summary = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "strategy": "rest buy-YES and buy-NO at `level` every 15m window (paper), touch-based fill sim from live Kalshi BBO",
           "level": bets[-1]["level"] if bets else 0.40, "contracts_per_leg": bets[-1]["contracts"] if bets else None, "start_cash": acct["start_cash"] if acct else None,
           "cash": round(acct["cash"], 2) if acct else None, "windows_settled": len(settled), "both": both, "single": single, "single_won": single_won, "none": none,
           "both_rate_of_filled": round(both / max(1, both + single), 4), "pnl": round(sum(b["pnl"] or 0 for b in settled), 2), "open_windows": len(bets) - len(settled),
           "by_day": sorted(by_day.values(), key=lambda x: x["day"])}
# only touch summary.json (and commit) when the tape itself changed — avoids a commit every 5 min
import hashlib
digest = hashlib.sha1(open(f"{HERE}/data/pair_bets.json", "rb").read() + open(f"{HERE}/data/quotes.csv", "rb").read()).hexdigest()
hp = f"{HERE}/.last_hash"
if os.path.exists(hp) and open(hp).read().strip() == digest:
    print(summary["generated_at"], "no change"); raise SystemExit(0)
open(hp, "w").write(digest)
json.dump(summary, open(f"{HERE}/data/summary.json", "w"), indent=1)
env = {**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}
def git(*a): return subprocess.run(["git", *a], cwd=HERE, env=env, capture_output=True, text=True)
if git("status", "--porcelain").stdout.strip():
    git("add", "-A"); git("commit", "-q", "-m", f"tape update {summary['generated_at']}: {len(settled)} settled, pnl {summary['pnl']:+.2f}")
    r = git("push", "-q"); print(summary["generated_at"], "pushed" if r.returncode == 0 else f"push failed: {r.stderr.strip()[:200]}")
else:
    print(summary["generated_at"], "no change")
