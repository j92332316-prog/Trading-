"""Point-in-time backtest of the frozen v1 rules: first trade 2026-10-19, last day 2026-11-10.

No-lookahead measures:
- signals use only data up to the signal day's close; fills at the NEXT day's open.
- monthly revenue of month M is used only for signal days AFTER the filing deadline
  (10th of M+1, moved to the next business day if it is a holiday).
- 60-day cost line / 20-day averages use trailing windows only.
Known residual: share counts (market-cap rank) come from the 2026-11-10 snapshot.

Usage: python src/backtest.py build | run
"""
import shutil, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sim, fetch

BT = sim.ROOT / "backtest"
PIT_REV, PIT_BASIC = BT / "revenue_pit", BT / "basic"
for p in (PIT_REV, PIT_BASIC):
    p.mkdir(parents=True, exist_ok=True)
# (ROC year, month, first signal day allowed to use it)
REV_SCHEDULE = [(115, 8, "20260911"), (115, 9, "20261013"), (115, 10, "20261111")]


def build():
    sim.LOOKBACK_TRADING_DAYS = 90          # 60 trading days before the 9/30 signal
    sim.build_history("20261110")
    for y, m, eff in REV_SCHEDULE:
        html = fetch.mops_revenue_html(y, m)
        if html is None:
            print(f"MOPS {y}/{m}: 無法確認"); continue
        df = pd.DataFrame(sim._parse_mops_html(html, f"{y}{m:02d}")).drop_duplicates("code")
        df.to_csv(PIT_REV / f"{eff}.csv", index=False)
        print(f"MOPS {y}/{m}: {len(df)} companies, usable from {eff}")
    shutil.copy(sim.BASIC / "20261110.csv", PIT_BASIC / "20260101.csv")


def run():
    sim.FIRST_SIGNAL, sim.FIRST_TRADE, sim.LAST_DAY = "20261016", "20261019", "20261110"
    sim.REV, sim.BASIC, sim.SIM = PIT_REV, PIT_BASIC, BT
    sim.write_notice = lambda *a, **k: None
    R = sim.replay("20261110")
    sim.write_outputs(R, "20261110")
    d = R["daily"]; eq, bn = d[-1]["equity"], d[-1]["bench"]
    sells = [t for t in R["trades"] if t["side"] == "SELL"]
    wins = [t for t in sells if t["pnl"] > 0]
    openp = [(c, p["shares"] * p["last"] * (1 - sim.SELL_COST) - p["cost"]) for c, p in R["pos"].items()]
    peak, mdd = 0, 0
    for r in d:
        peak = max(peak, r["equity"]); mdd = min(mdd, r["equity"] / peak - 1)
    out = [f"期間 {d[0]['date']}(訊號) ~ {d[-1]['date']}，交易日 {len(d)-1}",
           f"策略淨值 {eq:,.0f} ({eq/1e5-1:+.2%})｜0050 {bn:,.0f} ({bn/1e5-1:+.2%})｜差 {(eq-bn)/1e5:+.2%}",
           f"最大回撤 {mdd:.2%}｜買進 {sum(t['side']=='BUY' for t in R['trades'])} 筆｜已平倉 {len(sells)} 筆，賺 {len(wins)} 筆"
           + (f"，勝率 {len(wins)/len(sells):.0%}" if sells else ""),
           f"已實現損益 {sum(t['pnl'] for t in sells):,.0f}｜未平倉 {len(openp)} 檔，未實現(含賣出成本) {sum(x for _, x in openp):,.0f}",
           f"資料缺口日(無 T86) : {sorted(set(R['all_df']['date'].unique()) - set(R['all_df'][R['all_df'].trust_net.notna()]['date'].unique()))}"]
    (BT / "summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    {"build": build, "run": run}[sys.argv[1]]()
