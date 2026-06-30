from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


def main() -> None:
    legacy_output = Path(__file__).with_name("daily_prices.csv")
    bars_output = Path(__file__).with_name("daily_bars.csv")
    securities_output = Path(__file__).with_name("securities.csv")
    start = date(2026, 5, 1)
    stocks = [
        {
            "code": "600001",
            "name": "示例科技",
            "industry": "电子",
            "listing_date": "2016-03-15",
            "is_st": "false",
            "delisting_risk": "false",
            "base_close": 10.0,
            "daily_step": 0.08,
            "normal_amount": 120_000_000,
            "last_amount": 260_000_000,
            "turnover_rate": 4.2,
        },
        {
            "code": "000002",
            "name": "样本制造",
            "industry": "机械设备",
            "listing_date": "2012-07-10",
            "is_st": "false",
            "delisting_risk": "false",
            "base_close": 18.0,
            "daily_step": 0.02,
            "normal_amount": 80_000_000,
            "last_amount": 90_000_000,
            "turnover_rate": 1.8,
        },
        {
            "code": "300003",
            "name": "样本医药",
            "industry": "医药生物",
            "listing_date": "2025-01-20",
            "is_st": "false",
            "delisting_risk": "false",
            "base_close": 25.0,
            "daily_step": 0.16,
            "normal_amount": 150_000_000,
            "last_amount": 310_000_000,
            "turnover_rate": 13.5,
        },
        {
            "code": "600004",
            "name": "ST样本",
            "industry": "综合",
            "listing_date": "2009-11-02",
            "is_st": "true",
            "delisting_risk": "false",
            "base_close": 4.0,
            "daily_step": 0.01,
            "normal_amount": 60_000_000,
            "last_amount": 180_000_000,
            "turnover_rate": 6.0,
        },
    ]

    legacy_fieldnames = [
        "date",
        "code",
        "name",
        "industry",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "turnover_amount",
        "turnover_rate",
        "listing_date",
        "is_st",
        "delisting_risk",
    ]

    bars_fieldnames = [
        "date",
        "code",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "turnover_amount",
        "turnover_rate",
    ]

    securities_fieldnames = [
        "code",
        "name",
        "industry",
        "listing_date",
        "is_st",
        "delisting_risk",
        "exchange",
        "board",
    ]

    with securities_output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=securities_fieldnames)
        writer.writeheader()
        for stock in stocks:
            writer.writerow(
                {
                    "code": stock["code"],
                    "name": stock["name"],
                    "industry": stock["industry"],
                    "listing_date": stock["listing_date"],
                    "is_st": stock["is_st"],
                    "delisting_risk": stock["delisting_risk"],
                    "exchange": "SSE" if stock["code"].startswith("6") else "SZSE",
                    "board": "主板" if stock["code"].startswith(("6", "0")) else "创业板",
                }
            )

    with legacy_output.open("w", newline="", encoding="utf-8") as legacy_file, bars_output.open(
        "w", newline="", encoding="utf-8"
    ) as bars_file:
        writer = csv.DictWriter(legacy_file, fieldnames=legacy_fieldnames)
        bars_writer = csv.DictWriter(bars_file, fieldnames=bars_fieldnames)
        writer.writeheader()
        bars_writer.writeheader()
        for stock in stocks:
            for i in range(30):
                trade_date = start + timedelta(days=i)
                amount = stock["last_amount"] if i == 29 else stock["normal_amount"] + i * 500_000
                close = stock["base_close"] + i * stock["daily_step"]
                bar = {
                    "date": trade_date.isoformat(),
                    "code": stock["code"],
                    "open": round(close * 0.995, 2),
                    "high": round(close * 1.018, 2),
                    "low": round(close * 0.988, 2),
                    "close": round(close, 2),
                    "volume": int(amount / max(close, 0.01) / 100),
                    "turnover_amount": amount,
                    "turnover_rate": stock["turnover_rate"],
                }
                bars_writer.writerow(bar)
                writer.writerow(
                    {
                        **bar,
                        "name": stock["name"],
                        "industry": stock["industry"],
                        "listing_date": stock["listing_date"],
                        "is_st": stock["is_st"],
                        "delisting_risk": stock["delisting_risk"],
                    }
                )


if __name__ == "__main__":
    main()
