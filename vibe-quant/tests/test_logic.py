import math, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import sim

def test_cost_line_weights_by_lots_on_buy_days_only():
    h = pd.DataFrame({"close": [100, 110, 120, 130], "trust_net": [1000, -5000, 3000, 0]})
    # (1*100 + 3*120) / 4 = 115
    assert sim.cost_line(h) == 115

def test_cost_line_none_when_no_buys():
    assert math.isnan(sim.cost_line(pd.DataFrame({"close": [1.0], "trust_net": [-1.0]})))

def test_common_stock_filter():
    assert sim.is_common("2330")
    for c in ("0050", "00400A", "2881A", "9103", "910861"):
        assert not sim.is_common(c)

def test_round_trip_cost():
    assert abs(sim.BUY_COST + sim.SELL_COST - 0.00585) < 1e-12

def test_num_parsing():
    assert sim.num("1,234.5") == 1234.5 and math.isnan(sim.num("--"))

def test_entry_fires_when_all_four_conditions_hold():
    # regression: numpy bools must not break the all-four check
    days = [f"202601{d:02d}" for d in range(1, 23)]
    rows = [dict(date=d, code="1234", name="X", open=10, high=10, low=10, close=10 + i * 0.1,
                 volume=1000 if i < 21 else 5000, trust_net=1000) for i, d in enumerate(days)]
    all_df = pd.DataFrame(rows)
    basic = pd.DataFrame({"code": ["1234"], "industry": ["01"], "shares": [1e6]})
    rev = pd.DataFrame({"code": ["1234"], "ym": ["11412"], "yoy": [5.0], "src": ["t"]})
    sig = sim.evaluate(all_df, days[-1], basic, rev)
    assert bool(sig.iloc[0]["entry"]) is True
