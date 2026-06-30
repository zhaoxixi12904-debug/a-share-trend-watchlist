from __future__ import annotations

import argparse

from .config import ScreeningConfig
from .data_loader import load_daily_csv
from .providers import AkshareFetchConfig, fetch_akshare_daily
from .report import write_excel_report
from .screener import build_watchlist


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 A 股候选股票观察名单 Excel 报告。")
    parser.add_argument("--provider", choices=["csv", "akshare"], default="csv", help="数据源。默认 csv；akshare 会联网拉取。")
    parser.add_argument("--input", default=None, help="每日 A 股行情 CSV 路径。provider=csv 时必填。")
    parser.add_argument("--securities", default=None, help="证券主数据 CSV 路径。推荐包含名称、行业、上市日期、ST、退市风险。")
    parser.add_argument("--output", default="outputs/watchlist_report.xlsx", help="Excel 报告输出路径。")
    parser.add_argument("--as-of-date", default=None, help="指定筛选日期，例如 2026-06-30。默认使用 CSV 最新日期。")
    parser.add_argument("--start-date", default=None, help="AkShare 拉取开始日期，例如 2026-01-01。")
    parser.add_argument("--end-date", default=None, help="AkShare 拉取结束日期，例如 2026-06-30。")
    parser.add_argument("--symbols", default=None, help="AkShare 股票代码，逗号分隔，例如 600000,000001。")
    parser.add_argument("--max-symbols", type=int, default=None, help="AkShare 未指定 symbols 时最多拉取多少只，避免首次全市场拉太久。")
    parser.add_argument("--adjust", default="", help="AkShare 复权参数，空字符串为不复权。")
    parser.add_argument(
        "--industry-source",
        choices=["eastmoney", "none"],
        default="eastmoney",
        help="行业来源。provider=akshare 时默认使用东方财富行业板块。",
    )
    parser.add_argument("--industry-limit", type=int, default=None, help="调试用：只拉取前 N 个东方财富行业板块。")
    parser.add_argument("--min-amount", type=float, default=100_000_000, help="最低当日成交额，单位元。")
    parser.add_argument("--min-listing-days", type=int, default=180, help="最低上市天数。")
    parser.add_argument("--min-turnover", type=float, default=1.0, help="最低换手率，百分数数值。")
    parser.add_argument("--max-turnover", type=float, default=20.0, help="最高换手率，百分数数值。")
    parser.add_argument("--amount-spike-multiple", type=float, default=1.5, help="成交额放大倍数。")
    parser.add_argument("--max-5d-gain", type=float, default=0.25, help="近 5 日最大涨幅，例如 0.25。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ScreeningConfig(
        min_amount=args.min_amount,
        min_listing_days=args.min_listing_days,
        min_turnover=args.min_turnover,
        max_turnover=args.max_turnover,
        amount_spike_multiple=args.amount_spike_multiple,
        max_5d_gain=args.max_5d_gain,
        as_of_date=args.as_of_date,
    )

    if args.provider == "csv":
        if not args.input:
            raise SystemExit("provider=csv 时必须传入 --input。")
        raw = load_daily_csv(args.input, args.securities)
    else:
        if not args.start_date or not args.end_date:
            raise SystemExit("provider=akshare 时必须传入 --start-date 和 --end-date。")
        symbols = [item.strip() for item in args.symbols.split(",")] if args.symbols else None
        raw = fetch_akshare_daily(
            AkshareFetchConfig(
                start_date=args.start_date,
                end_date=args.end_date,
                symbols=symbols,
                max_symbols=args.max_symbols,
                adjust=args.adjust,
                industry_source=args.industry_source,
                industry_limit=args.industry_limit,
            )
        )
    report = build_watchlist(raw, config)
    output = write_excel_report(report, args.output, config)
    print(f"观察名单报告已生成：{output}")
    print(f"候选数量：{len(report)}")


if __name__ == "__main__":
    main()
