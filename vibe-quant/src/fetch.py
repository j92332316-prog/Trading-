"""Paced, cached fetchers for the only allowed sources: TWSE / MOPS / TPEx.

Rules:
- Honest User-Agent, >= PACE seconds between requests, exponential backoff when the
  TWSE WAF answers with its "FOR SECURITY REASONS" page. No proxies, no UA spoofing.
- Every successful raw response is cached under data/raw/ so we never re-hit a URL.
- Missing data is returned as None; callers must mark it "無法確認", never fill it in.
"""
from __future__ import annotations

import json
import os
import time
import hashlib
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

UA = "vibe-quant-sim/1.0 (paper trading research)"
PACE = float(os.environ.get("VQ_PACE", "5"))
_last = [0.0]


class Blocked(Exception):
    pass


def _get(url: str, max_tries: int = 5, encoding: str | None = None) -> str:
    cache = _cache_path(url)
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    wait = 30
    for attempt in range(max_tries):
        dt = time.time() - _last[0]
        if dt < PACE:
            time.sleep(PACE - dt)
        _last[0] = time.time()
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=60, allow_redirects=False)
        except requests.RequestException as e:  # network hiccup
            print(f"  ! {e.__class__.__name__} on {url}; retry in {wait}s")
            time.sleep(wait); wait *= 2
            continue
        if encoding:
            r.encoding = encoding
        txt = r.text
        if r.status_code != 200 or "FOR SECURITY REASONS" in txt:
            print(f"  ! HTTP {r.status_code} / WAF on {url}; backoff {wait}s")
            time.sleep(wait); wait *= 2
            continue
        cache.write_text(txt, encoding="utf-8")
        return txt
    raise Blocked(url)


def _cache_path(url: str) -> Path:
    return RAW / f"{hashlib.sha1(url.encode()).hexdigest()[:16]}.txt"


def _json(url: str):
    j = json.loads(_get(url))
    # never keep a "no data yet" answer in cache (e.g. today's data before publication)
    if isinstance(j, dict) and j.get("stat") not in (None, "OK"):
        _cache_path(url).unlink(missing_ok=True)
    return j


# ---------- TWSE daily quotes (all listed securities) ----------
def mi_index(date: str):
    """date=YYYYMMDD. Returns list[dict] of per-stock OHLCV, or [] on non-trading day."""
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={date}&type=ALLBUT0999&response=json"
    j = _json(url)
    if j.get("stat") != "OK":
        return []
    for t in j.get("tables", []):
        f = t.get("fields") or []
        if "證券代號" in f and "開盤價" in f:
            return [dict(zip(f, row)) for row in t["data"]]
    return []


# ---------- TWSE 三大法人買賣超日報 ----------
def t86(date: str):
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date}&selectType=ALLBUT0999&response=json"
    j = _json(url)
    if j.get("stat") != "OK":
        return []
    f = j["fields"]
    return [dict(zip(f, row)) for row in j["data"]]


# ---------- TWSE OpenAPI ----------
def company_basic():
    """上市公司基本資料 (shares outstanding, industry)."""
    return _json("https://openapi.twse.com.tw/v1/opendata/t187ap03_L")


def monthly_revenue_openapi():
    """上市公司每月營業收入彙總表 (latest month TWSE has published)."""
    return _json("https://openapi.twse.com.tw/v1/opendata/t187ap05_L")


def mops_revenue_html(roc_year: int, month: int):
    """MOPS 上市公司月營收彙總 (static HTML, Big5). Returns raw HTML or None."""
    url = f"https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_{roc_year}_{month}_0.html"
    try:
        return _get(url, encoding="big5")
    except Blocked:
        return None


def nocache_get(url):
    """Used only for probing; not cached."""
    return requests.get(url, headers={"User-Agent": UA}, timeout=60, allow_redirects=False)
