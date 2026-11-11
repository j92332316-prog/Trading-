"""Technical snapshot for a watchlist, from stored TWSE/TPEx daily data (no forecasts)."""
import os, sys, math
import pandas as pd
CODES = "7856 5274 2454 2330 5347 3443 2303 2382 2317 2308 3711 3017 2059 2344 2408 8299 5289 2395 1303 6442 3081 2383 6274 2327 3037 2881 2890 2603 2637 6418 3563 6526 2409 2404 2481 1815 6672 8039 8358 8046 3189 4958 8021".split()
def load(folder, mkt):
    fr = []
    for f in sorted(os.listdir(folder)):
        d = pd.read_csv(f"{folder}/{f}", dtype={"code": str}); d = d[d.code.isin(CODES)].copy()
        d["date"] = f[:8]; d["mkt"] = mkt; fr.append(d)
    return pd.concat(fr) if fr else pd.DataFrame()
df = pd.concat([load("data/daily", "市"), load("data/tpex", "櫃")])
rows = []
for c in CODES:
    h = df[df.code == c].sort_values("date").dropna(subset=["close"])
    if len(h) < 21:
        rows.append(dict(code=c, note=f"資料不足({len(h)}日)")); continue
    cl, hi, lo, v = h.close, h.high, h.low, h.volume
    last = cl.iloc[-1]; ma = lambda n: cl.tail(n).mean() if len(cl) >= n else math.nan
    ch = cl.diff(); up = ch.clip(lower=0).tail(14).mean(); dn = (-ch.clip(upper=0)).tail(14).mean()
    rsi = 100 - 100 / (1 + up / dn) if dn > 0 else 100
    tr = pd.concat([hi - lo, (hi - cl.shift()).abs(), (lo - cl.shift()).abs()], axis=1).max(axis=1)
    atr = tr.tail(14).mean() / last * 100
    h60 = hi.tail(60).max(); l20 = lo.tail(20).min(); ph20 = hi.iloc[-21:-1].max()
    tn = h.trust_net.tail(5) if "trust_net" in h and h.trust_net.notna().any() else None
    rows.append(dict(code=c, name=h.name.iloc[-1], mkt=h.mkt.iloc[-1], n=len(h), close=last,
        d1=cl.iloc[-1] / cl.iloc[-2] - 1, d5=cl.iloc[-1] / cl.iloc[-6] - 1, d20=cl.iloc[-1] / cl.iloc[-21] - 1,
        vsMA5=last / ma(5) - 1, vsMA20=last / ma(20) - 1, vsMA60=last / ma(60) - 1 if len(cl) >= 60 else math.nan,
        ma20up=ma(20) > cl.iloc[-25:-5].mean(), rsi=rsi, atr=atr,
        volx=v.iloc[-1] / v.iloc[-21:-1].mean(), from60h=last / h60 - 1, brk20=last > ph20,
        stop20=l20 / last - 1, trust5=(tn.sum() / 1000 if tn is not None else math.nan),
        trustdays=(int((tn > 0).sum()) if tn is not None else -1)))
out = pd.DataFrame(rows); out.to_csv("sim/watchlist_ta_20261111.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 99)
f = out.copy()
for k in ["d1","d5","d20","vsMA5","vsMA20","vsMA60","from60h","stop20"]:
    f[k] = (f[k] * 100).round(1)
for k in ["rsi","atr","volx"]: f[k] = f[k].round(1)
f["trust5"] = f["trust5"].round(0)
print(f.drop(columns=["n"]).to_string(index=False))
