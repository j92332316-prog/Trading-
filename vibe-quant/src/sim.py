"""Vibe 量化 v1 paper-trading simulator (2026-11-11 ~ 2026-11-17).

Deterministic replay: every run rebuilds the whole ledger from the first signal day
using the committed daily snapshots in data/daily and data/revenue, so the ledger is
reproducible and never edited by hand.

Usage:
  python src/sim.py build  [--asof YYYYMMDD]   # fetch & store snapshots (paced)
  python src/sim.py run    [--asof YYYYMMDD]   # replay, write ledger + notification
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "data" / "daily"
REV = ROOT / "data" / "revenue"
BASIC = ROOT / "data" / "basic"
SIM = ROOT / "sim"
NOTE = ROOT / "notifications"
for p in (DAILY, REV, BASIC, SIM, NOTE):
    p.mkdir(parents=True, exist_ok=True)

FIRST_SIGNAL = "20261110"
FIRST_TRADE = "20261111"
LAST_DAY = "20261117"
CAPITAL = 100_000
SLOTS = 5
ALLOC = 20_000
BUY_COST = 0.001425
SELL_COST = 0.004425          # 0.1425% fee + 0.3% tax  -> round trip 0.585%
LOOKBACK_TRADING_DAYS = 62    # 60-day cost line + 3-day streak margin
BENCH = "0050"
UNCONFIRMED = "無法確認"


# ---------------------------------------------------------------- helpers
def num(x):
    if x is None:
        return math.nan
    s = str(x).replace(",", "").strip()
    if s in ("", "--", "---", "X", "除權息", "除息", "除權"):
        return math.nan
    try:
        return float(s)
    except ValueError:
        return math.nan


def ymd(d: dt.date) -> str:
    return d.strftime("%Y%m%d")


def pdate(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y%m%d").date()


def fmt_d(s: str) -> str:
    return f"{s[4:6]}/{s[6:]}"


# ---------------------------------------------------------------- data build
def daily_path(d: str) -> Path:
    return DAILY / f"{d}.csv"


def build_day(d: str) -> str:
    """Store one trading day's quotes + 投信 net. Returns 'trading'|'closed'|'partial'."""
    p = daily_path(d)
    if p.exists():
        df = pd.read_csv(p, dtype={"code": str})
        if df["trust_net"].notna().any():
            return "trading"
    else:
        rows = fetch.mi_index(d)
        if not rows:
            return "closed"
        df = pd.DataFrame({
            "code": [r["證券代號"].strip() for r in rows],
            "name": [r["證券名稱"].strip() for r in rows],
            "open": [num(r["開盤價"]) for r in rows],
            "high": [num(r["最高價"]) for r in rows],
            "low": [num(r["最低價"]) for r in rows],
            "close": [num(r["收盤價"]) for r in rows],
            "volume": [num(r["成交股數"]) for r in rows],
        })
        df["trust_net"] = math.nan
    try:
        t = fetch.t86(d)
    except fetch.Blocked:
        t = []
    if t:
        key = next(k for k in t[0] if "投信買賣超股數" in k)
        m = {r["證券代號"].strip(): num(r[key]) for r in t}
        # T86 lists every stock with any institutional activity; absent = 0 投信 net
        df["trust_net"] = df["code"].map(m).fillna(0.0)
    df.to_csv(p, index=False)
    return "trading" if t else "partial"


def build_history(asof: str):
    d = pdate(asof)
    have = 0
    while have < LOOKBACK_TRADING_DAYS:
        if d.weekday() < 5:
            s = ymd(d)
            st = build_day(s)
            if st != "closed":
                have += 1
            print(f"{s} {st}", flush=True)
        d -= dt.timedelta(days=1)


def build_basic(asof: str):
    p = BASIC / f"{asof}.csv"
    if p.exists():
        return
    b = fetch.company_basic()
    rows = []
    for r in b:
        code = r.get("公司代號", "").strip()
        shares_key = next((k for k in r if "已發行普通股數" in k), None)
        rows.append({
            "code": code,
            "industry": r.get("產業別", "").strip(),
            "shares": num(r.get(shares_key)) if shares_key else math.nan,
        })
    pd.DataFrame(rows).to_csv(p, index=False)


def _parse_mops_html(html: str, ym: str):
    out = []
    for t in pd.read_html(io.StringIO(html)):
        cols = [re.sub(r"\s+", "", "".join(map(str, c)) if isinstance(c, tuple) else str(c))
                for c in t.columns]
        t.columns = cols
        code_c = next((c for c in cols if "公司代號" in c), None)
        yoy_c = next((c for c in cols if "去年同月增減" in c), None)
        if not code_c or not yoy_c:
            continue
        for _, r in t.iterrows():
            code = str(r[code_c]).strip()
            if re.fullmatch(r"\d{4}", code):
                out.append({"code": code, "ym": ym, "yoy": num(r[yoy_c]), "src": "MOPS"})
    return out


def build_revenue(asof: str):
    """Snapshot of the latest published monthly revenue YoY per company as of `asof`."""
    p = REV / f"{asof}.csv"
    if p.exists():
        return
    rows = []
    for r in fetch.monthly_revenue_openapi():
        ym = r.get("資料年月", "").strip()          # ROC yyyMM, e.g. 11509
        rows.append({"code": r.get("公司代號", "").strip(), "ym": ym,
                     "yoy": num(r.get("營業收入-去年同月增減(%)")), "src": "TWSE OpenAPI"})
    # MOPS for the month that must be published by the 10th of `asof`'s month
    d = pdate(asof)
    prev = (d.replace(day=1) - dt.timedelta(days=1))
    roc_y, m = prev.year - 1911, prev.month
    html = fetch.mops_revenue_html(roc_y, m)
    if html:
        rows += _parse_mops_html(html, f"{roc_y}{m:02d}")
    df = pd.DataFrame(rows)
    df = df[df["code"].str.fullmatch(r"\d{4}")]
    df = df.sort_values(["code", "ym"]).groupby("code").tail(1)
    df.to_csv(p, index=False)


# ---------------------------------------------------------------- analytics
def load_days(upto: str):
    files = sorted(f for f in DAILY.glob("*.csv") if f.stem <= upto)
    frames = []
    for f in files:
        df = pd.read_csv(f, dtype={"code": str})
        df["date"] = f.stem
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def is_common(code: str) -> bool:
    return bool(re.fullmatch(r"[1-9]\d{3}", code)) and not code.startswith("91")


def universe(day_df: pd.DataFrame, basic: pd.DataFrame) -> pd.DataFrame:
    df = day_df[day_df["code"].map(is_common)].merge(basic, on="code", how="left")
    df = df[~df["industry"].astype(str).isin(["91", "存託憑證"])]
    df["mcap"] = df["close"] * df["shares"]
    df = df.dropna(subset=["mcap"]).sort_values("mcap", ascending=False).head(100)
    df["rank"] = range(1, len(df) + 1)
    return df


def cost_line(hist: pd.DataFrame):
    """hist: one stock's rows, sorted by date, last 60 trading days."""
    h = hist.tail(60)
    if h["trust_net"].isna().any():      # a day without T86 -> 無法確認, never guessed
        return math.nan
    buy = h[h["trust_net"] > 0]
    if buy.empty:
        return math.nan
    lots = buy["trust_net"] / 1000
    return float((lots * buy["close"]).sum() / lots.sum())


def evaluate(all_df: pd.DataFrame, d: str, basic: pd.DataFrame, rev: pd.DataFrame):
    """Return (universe_df with signal columns) for signal day d."""
    dates = sorted(all_df["date"].unique())
    dates = [x for x in dates if x <= d]
    day = all_df[all_df["date"] == d]
    uni = universe(day, basic)
    rev_m = rev.set_index("code")
    recs = []
    for _, u in uni.iterrows():
        h = all_df[all_df["code"] == u["code"]].sort_values("date")
        h = h[h["date"] <= d]
        last3 = h.tail(3)["trust_net"]
        c = {"code": u["code"], "name": u["name"], "rank": u["rank"], "close": u["close"]}
        c["trust3"] = (bool((last3 > 0).all()) if len(last3) == 3 and last3.notna().all() else None)
        c["ma20"] = h.tail(20)["close"].mean() if len(h) >= 20 else math.nan
        prev20 = h.iloc[-21:-1]["volume"] if len(h) >= 21 else pd.Series(dtype=float)
        c["vol"] = u["volume"]
        c["vma20"] = prev20.mean() if len(prev20) == 20 else math.nan
        c["above_ma"] = (u["close"] > c["ma20"]) if not math.isnan(c["ma20"]) else None
        c["vol_ok"] = (u["volume"] > 1.5 * c["vma20"]) if not math.isnan(c["vma20"]) else None
        if u["code"] in rev_m.index and not math.isnan(rev_m.loc[u["code"], "yoy"]):
            c["rev_ym"] = str(rev_m.loc[u["code"], "ym"])
            c["rev_yoy"] = float(rev_m.loc[u["code"], "yoy"])
            c["rev_ok"] = c["rev_yoy"] > 0
        else:
            c["rev_ym"], c["rev_yoy"], c["rev_ok"] = UNCONFIRMED, math.nan, None
        c["cost_line"] = cost_line(h)
        flags = [c["trust3"], c["above_ma"], c["vol_ok"], c["rev_ok"]]
        c["unconfirmed"] = any(f is None for f in flags)
        c["entry"] = all(f is True for f in flags)
        recs.append(c)
    return pd.DataFrame(recs)


def exit_check(all_df, d, code):
    h = all_df[(all_df["code"] == code) & (all_df["date"] <= d)].sort_values("date")
    cl = cost_line(h)
    close = float(h.iloc[-1]["close"]) if not h.empty else math.nan
    if math.isnan(cl) or math.isnan(close):
        return None, close, cl
    return close < cl, close, cl


# ---------------------------------------------------------------- replay
def snapshot_for(folder: Path, d: str):
    """Latest snapshot file on or before d (point-in-time)."""
    fs = sorted(f for f in folder.glob("*.csv") if f.stem <= d)
    if not fs:
        return None
    return pd.read_csv(fs[-1], dtype={"code": str, "ym": str, "industry": str})


def replay(asof: str):
    all_df = load_days(asof)
    tdays = sorted(x for x in all_df["date"].unique() if FIRST_SIGNAL <= x <= min(asof, LAST_DAY))
    # a day is usable only if T86 data exists
    tdays = [x for x in tdays if all_df[all_df["date"] == x]["trust_net"].notna().any()]
    cash = float(CAPITAL)
    pos: dict[str, dict] = {}
    trades, daily, events = [], [], {}
    pending = {"buy": [], "sell": [], "signal_date": None}
    bench = None
    signals_by_day = {}
    for d in tdays:
        ev = events.setdefault(d, {"filled": [], "unfilled": []})
        day = all_df[all_df["date"] == d].set_index("code")
        # 1) execute yesterday's orders at today's open
        if d >= FIRST_TRADE:
            for code in pending["sell"]:
                if code not in pos:
                    continue
                o = day["open"].get(code, math.nan)
                if math.isnan(o):
                    ev["unfilled"].append(("賣出", code, "今日無開盤價，順延"))
                    continue
                p = pos.pop(code)
                gross = p["shares"] * o
                fee = gross * SELL_COST
                cash += gross - fee
                pnl = gross - fee - p["cost"]
                t = dict(date=d, side="SELL", code=code, name=p["name"], shares=p["shares"],
                         price=o, fee=round(fee, 2), net=round(gross - fee, 2),
                         pnl=round(pnl, 2), ret=pnl / p["cost"], signal=pending["signal_date"])
                trades.append(t); ev["filled"].append(t)
            for code, name in pending["buy"]:
                if code in pos or len(pos) >= SLOTS:
                    if len(pos) >= SLOTS:
                        ev["unfilled"].append(("買進", code, "名額已滿"))
                    continue
                o = day["open"].get(code, math.nan)
                if math.isnan(o) or o <= 0:
                    ev["unfilled"].append(("買進", code, "今日無開盤價"))
                    continue
                sh = int(ALLOC // o)
                gross = sh * o
                fee = gross * BUY_COST
                if sh == 0 or gross + fee > cash:
                    ev["unfilled"].append(("買進", code, "現金不足"))
                    continue
                cash -= gross + fee
                pos[code] = dict(name=name, shares=sh, entry=o, entry_date=d, cost=gross + fee)
                t = dict(date=d, side="BUY", code=code, name=name, shares=sh, price=o,
                         fee=round(fee, 2), net=round(-(gross + fee), 2), pnl=None, ret=None,
                         signal=pending["signal_date"])
                trades.append(t); ev["filled"].append(t)
            if bench is None:
                o = day["open"].get(BENCH, math.nan)
                sh = int(CAPITAL // (o * (1 + BUY_COST)))
                bench = dict(shares=sh, entry=o, cash=CAPITAL - sh * o * (1 + BUY_COST))
        # 2) mark to market
        mv = 0.0
        for code, p in pos.items():
            c = day["close"].get(code, math.nan)
            p["last"] = c if not math.isnan(c) else p.get("last", p["entry"])
            mv += p["shares"] * p["last"]
        bval = (bench["shares"] * day["close"].get(BENCH, math.nan) + bench["cash"]) if bench else CAPITAL
        daily.append(dict(date=d, cash=cash, mv=mv, equity=cash + mv, bench=bval,
                          npos=len(pos)))
        # 3) signals for next open
        basic = snapshot_for(BASIC, d)
        rev = snapshot_for(REV, d)
        sig = evaluate(all_df, d, basic, rev)
        signals_by_day[d] = sig
        sells = []
        exits_info = {}
        for code in pos:
            hit, c, cl = exit_check(all_df, d, code)
            exits_info[code] = (hit, c, cl)
            if hit:
                sells.append(code)
        free = SLOTS - (len(pos) - len(sells))
        cands = sig[sig["entry"] & ~sig["code"].isin(pos.keys())].sort_values("rank")
        buys = list(zip(cands["code"], cands["name"]))
        pending = {"buy": buys[:max(free, 0)], "sell": sells, "signal_date": d,
                   "waitlist": buys[max(free, 0):], "exits_info": exits_info}
        if d == LAST_DAY:
            pending["final"] = True
        ev["pending"] = pending
    return dict(tdays=tdays, cash=cash, pos=pos, trades=trades, daily=daily,
                events=events, bench=bench, signals=signals_by_day, all_df=all_df)


# ---------------------------------------------------------------- reporting
def money(x):
    return f"{x:,.0f}"


def pct(x):
    return f"{x*100:+.2f}%"


def write_outputs(R, asof):
    tdays = R["tdays"]
    if not tdays:
        print("no usable trading day yet")
        return
    last = tdays[-1]
    L = ["# Vibe 量化 v1 模擬帳本（紙上交易）", "",
         f"- 最後更新資料日：{last}　（由 `src/sim.py run` 從 {FIRST_SIGNAL} 起完整重播產生，請勿手改）",
         "- 規則：`v1_select.md`（凍結）；補充解釋見 `change_log.md`",
         "- 資料來源：TWSE（MI_INDEX、T86、OpenAPI t187ap03_L / t187ap05_L）、MOPS 月營收彙總", ""]
    L += ["## 每日淨值", "", "| 日期 | 現金 | 持股市值 | 總淨值 | 報酬 | 0050 基準 | 基準報酬 | 持股數 |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in R["daily"]:
        L.append(f"| {r['date']} | {money(r['cash'])} | {money(r['mv'])} | {money(r['equity'])} | "
                 f"{pct(r['equity']/CAPITAL-1)} | {money(r['bench'])} | {pct(r['bench']/CAPITAL-1)} | {r['npos']} |")
    L += ["", "## 成交紀錄", "", "| 成交日 | 訊號日 | 買賣 | 代號 | 名稱 | 股數 | 成交價(開盤) | 費用 | 損益 | 報酬 |",
          "|---|---|---|---|---|---:|---:|---:|---:|---:|"]
    for t in R["trades"]:
        L.append(f"| {t['date']} | {t['signal']} | {'買進' if t['side']=='BUY' else '賣出'} | {t['code']} | {t['name']} | "
                 f"{t['shares']:,} | {t['price']:.2f} | {t['fee']:.0f} | "
                 f"{'' if t['pnl'] is None else money(t['pnl'])} | {'' if t['ret'] is None else pct(t['ret'])} |")
    if not R["trades"]:
        L.append("| （尚無成交） | | | | | | | | | |")
    L += ["", "## 目前持股", "", "| 代號 | 名稱 | 進場日 | 股數 | 進場價 | 收盤 | 投信成本線(估) | 未實現損益 |",
          "|---|---|---|---:|---:|---:|---:|---:|"]
    ex = R["events"][last].get("pending", {}).get("exits_info", {})
    for code, p in R["pos"].items():
        cl = ex.get(code, (None, None, math.nan))[2]
        unr = p["shares"] * p["last"] * (1 - SELL_COST) - p["cost"]
        L.append(f"| {code} | {p['name']} | {p['entry_date']} | {p['shares']:,} | {p['entry']:.2f} | {p['last']:.2f} | "
                 f"{'無法確認' if cl is None or math.isnan(cl) else f'{cl:.2f}'} | {money(unr)}（含賣出成本） |")
    if not R["pos"]:
        L.append("| （空手） | | | | | | | |")
    (SIM / "ledger.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # signal detail per day
    for d, sig in R["signals"].items():
        s = sig.copy()
        s.to_csv(SIM / f"signals_{d}.csv", index=False)

    write_notice(R, last)


def write_notice(R, d):
    ev = R["events"][d]
    pend = ev.get("pending", {})
    nd = next_trading_label(d)
    L = [f"🔔 模擬交易通知｜{fmt_d(d)}（紙上交易，非真實下單）", ""]
    if d >= FIRST_TRADE:
        L.append(f"📥 今日（{fmt_d(d)}）開盤模擬成交：")
        if ev["filled"]:
            for t in ev["filled"]:
                if t["side"] == "BUY":
                    L.append(f"- 🟢 買進 {t['code']} {t['name']}　{t['shares']:,} 股 @ {t['price']:.2f}　成本 {money(-t['net'])}")
                else:
                    L.append(f"- 🔴 賣出 {t['code']} {t['name']}　{t['shares']:,} 股 @ {t['price']:.2f}　損益 {money(t['pnl'])}（{pct(t['ret'])}）")
        else:
            L.append("- 無")
        for side, code, why in ev["unfilled"]:
            L.append(f"- ⚠️ 未成交：{side} {code}（{why}）")
        r = R["daily"][-1]
        L += ["", f"💼 收盤淨值 {money(r['equity'])}（{pct(r['equity']/CAPITAL-1)}）｜0050 基準 {money(r['bench'])}（{pct(r['bench']/CAPITAL-1)}）｜持股 {r['npos']} 檔", ""]
    if pend.get("final"):
        L.append("🏁 模擬期最後一天，今日訊號不再執行。")
    else:
        L.append(f"📅 {nd} 開盤預定（依 {fmt_d(d)} 收盤訊號）：")
        if not pend.get("buy") and not pend.get("sell"):
            L.append("- 無")
        for code in pend.get("sell", []):
            _, c, cl = pend["exits_info"][code]
            L.append(f"- 🔴 賣出 {code} {R['pos'][code]['name']}（收盤 {c:.2f} < 投信成本線估 {cl:.2f}）")
        sig = R["signals"][d].set_index("code")
        for code, name in pend.get("buy", []):
            s = sig.loc[code]
            L.append(f"- 🟢 買進 {code} {name}（市值第 {int(s['rank'])} 名；收 {s['close']:.2f} > MA20 {s['ma20']:.2f}；"
                     f"量 {s['vol']/s['vma20']:.2f} 倍；營收 {s['rev_ym']} YoY {s['rev_yoy']:+.1f}%）")
        for code, name in pend.get("waitlist", []):
            L.append(f"- ⏸️ 候補（名額不足）{code} {name}")
    sig = R["signals"][d]
    nunc = int(sig["unconfirmed"].sum())
    if nunc:
        L += ["", f"ℹ️ 股池中 {nunc} 檔有資料「無法確認」（明細見 sim/signals_{d}.csv），當日不評估進場。"]
    (NOTE / f"{d}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def next_trading_label(d):
    x = pdate(d) + dt.timedelta(days=1)
    while x.weekday() >= 5:
        x += dt.timedelta(days=1)
    return f"{x.month:02d}/{x.day:02d}（預估交易日）"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "run"])
    ap.add_argument("--asof", default=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d"))
    a = ap.parse_args()
    asof = min(a.asof, LAST_DAY)
    if a.cmd == "build":
        build_basic(asof)
        build_revenue(asof)
        build_history(asof)
    else:
        R = replay(asof)
        write_outputs(R, asof)
        (SIM / "state.json").write_text(json.dumps(
            {"asof": asof, "days": R["daily"], "trades": R["trades"],
             "positions": R["pos"]}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
