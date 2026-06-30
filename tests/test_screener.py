from datetime import date, timedelta

import pandas as pd

from a_share_watchlist.config import ScreeningConfig
from a_share_watchlist.data_loader import load_daily_csv
from a_share_watchlist.screener import build_watchlist


def test_build_watchlist_returns_only_allowed_actions():
    rows = []
    start = date(2026, 5, 1)
    for i in range(30):
        current = start + timedelta(days=i)
        rows.append(
            {
                "date": current.isoformat(),
                "code": "600001",
                "name": "示例科技",
                "industry": "电子",
                "close": 10 + i * 0.1,
                "turnover_amount": 100_000_000 if i < 29 else 260_000_000,
                "turnover_rate": 4.5,
                "listing_date": "2020-01-01",
                "is_st": False,
                "delisting_risk": False,
            }
        )

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["listing_date"] = pd.to_datetime(df["listing_date"])

    report = build_watchlist(df, ScreeningConfig(min_amount=50_000_000))

    assert len(report) == 1
    assert set(report["建议动作"]).issubset({"观察", "等待回调", "排除"})
    assert report.loc[0, "股票代码"] == "600001"


def test_load_split_daily_bars_and_securities(tmp_path):
    bars = tmp_path / "daily_bars.csv"
    securities = tmp_path / "securities.csv"
    bars.write_text(
        "date,code,open,high,low,close,volume,turnover_amount,turnover_rate\n"
        "2026-06-01,600001,10,10.5,9.8,10.2,100000,120000000,3.2\n",
        encoding="utf-8",
    )
    securities.write_text(
        "code,name,industry,listing_date,is_st,delisting_risk\n"
        "600001,示例科技,电子,2020-01-01,false,false\n",
        encoding="utf-8",
    )

    df = load_daily_csv(bars, securities)

    assert df.loc[0, "name"] == "示例科技"
    assert df.loc[0, "industry"] == "电子"
