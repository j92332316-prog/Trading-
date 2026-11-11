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
