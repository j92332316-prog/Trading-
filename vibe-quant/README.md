# vibe-quant v1 模擬盤（紙上交易，2026-11-11 ～ 11-17）

不下真實委託、不連券商、不用槓桿。規則見 `v1_select.md`（凍結），規格補充與想改的地方見 `change_log.md`。

## 每日流程（台北 17:25 自動排程觸發）
```bash
cd vibe-quant
VQ_PACE=6 python3 src/sim.py build --asof YYYYMMDD   # 抓 TWSE/MOPS，資料存 data/
python3 src/sim.py run   --asof YYYYMMDD             # 從 11/10 完整重播 → sim/ledger.md、notifications/YYYYMMDD.md
python3 -m pytest -q tests
```

## 檔案
| 路徑 | 內容 |
|---|---|
| `sim/ledger.md` | 帳本：每日淨值 vs 0050、成交紀錄、持股 |
| `sim/signals_YYYYMMDD.csv` | 股池前 100 名逐檔四條件判斷、投信成本線 |
| `notifications/YYYYMMDD.md` | 🔔 每日通知全文 |
| `data/daily/` | 每日行情＋投信買賣超（TWSE MI_INDEX、T86） |
| `data/revenue/` | 當日可取得的最新月營收（MOPS t21sc03，缺漏以 TWSE OpenAPI 補，並標示月份） |
| `data/basic/` | 已發行普通股數、產業別（TWSE OpenAPI t187ap03_L） |

## 已知限制
- TWSE / MOPS 的 WAF 會對雲端 IP 限速；程式以 ≥6 秒間隔、指數退避重試，不偽裝 UA。
- 投信成本線是估計值（以買超日收盤價代替成交均價）。
- 零股成交假設：以開盤價全數成交，未計滑價。
