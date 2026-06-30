from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from a_share_watchlist.config import ScreeningConfig
from a_share_watchlist.data_loader import merge_daily_with_securities
from a_share_watchlist.screener import build_watchlist
from a_share_watchlist.trend_report import write_trend_report


TARGET_INDUSTRIES = [
    ("新型储能与电池", ["电池", "锂电池", "电池化学品", "蓄电池及其他电池"]),
    ("新型电力系统", ["电网设备", "电网自动化设备", "电力设备", "综合电力设备商"]),
    ("AI算力与国产硬件", ["通信网络设备及器件", "通信设备", "半导体", "半导体设备", "数字芯片设计"]),
    ("创新药与医疗研发", ["生物制品", "医疗研发外包", "医药生物"]),
]

THESIS_ROWS = [
    {
        "主题": "新型储能与电池",
        "趋势判断": "景气度较高",
        "主要依据": "国家能源局信息显示，新型储能正在深度融入新型电力系统建设；截至2025年底，中国新型储能规模已处于全球领先位置，政策机制、技术迭代和新能源消纳需求形成共同驱动。",
        "观察方向": "电池、锂电池、电池材料、储能系统相关公司。",
        "来源": "https://www.nea.gov.cn/20260417/a6ef89bc89eb4814872959c4b10fd731/c.html",
    },
    {
        "主题": "新型电力系统",
        "趋势判断": "中长期向好",
        "主要依据": "发改委、国家能源局推动多用户绿电直连，支持工业园区、零碳园区、算力设施等场景提升新能源就近消纳，电网设备和电力系统调节能力重要性上升。",
        "观察方向": "电网设备、电网自动化、电力设备。",
        "来源": "https://www.ndrc.gov.cn/xxgk/zcfb/tz/202605/t20260520_1405313.html",
    },
    {
        "主题": "AI算力与国产硬件",
        "趋势判断": "结构性机会较多",
        "主要依据": "国务院“人工智能+”行动强调智能算力统筹、模型基础能力、数据供给和产业应用，算力基础设施、通信设备、半导体和软件生态是基础支撑。",
        "观察方向": "通信设备、半导体、芯片设计、软件开发。",
        "来源": "https://www.news.cn/politics/20250826/21f5785636b14373af2e5d85ef383344/c.html",
    },
    {
        "主题": "创新药与医疗研发",
        "趋势判断": "政策环境改善",
        "主要依据": "国家医保局发布基本医保目录和首版商业健康保险创新药目录，创新药支付和多层次保障体系逐步完善，有利于临床价值高的创新药及研发服务链条。",
        "观察方向": "生物制品、医疗研发外包、医药生物。",
        "来源": "https://www.nhsa.gov.cn/art/2025/12/7/art_14_18972.html",
    },
]


def main() -> None:
    output = ROOT / "outputs" / "trend_watchlist_2026.xlsx"
    industry_lookup = fetch_industry_lookup()
    selected = select_symbols(industry_lookup, per_industry=10)
    if not selected:
        raise RuntimeError("没有选出任何股票代码。")

    daily, securities = fetch_daily_and_securities(selected)
    raw = merge_daily_with_securities(daily, securities)
    config = ScreeningConfig(
        min_amount=50_000_000,
        min_listing_days=180,
        min_turnover=0.5,
        max_turnover=35,
        amount_spike_multiple=1.2,
        max_5d_gain=0.35,
    )
    watchlist = build_watchlist(raw, config)
    if watchlist.empty:
        watchlist = build_fallback_watchlist(raw)

    trend_snapshot = build_trend_snapshot(raw, watchlist)
    write_trend_report(pd.DataFrame(THESIS_ROWS), watchlist, trend_snapshot, output)
    print(output)
    print(f"候选股票池：{len(selected)}")
    print(f"观察名单：{len(watchlist)}")


def fetch_industry_lookup() -> dict[str, tuple[str, str]]:
    url = "https://17.push2.eastmoney.com/api/qt/clist/get"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/center/boardlist.html"}
    rows: dict[str, tuple[str, str]] = {}
    for page in range(1, 8):
        params = {
            "pn": page,
            "pz": 100,
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:90 t:2 f:!50",
            "fields": "f12,f14",
        }
        data = requests.get(url, params=params, headers=headers, timeout=20).json()["data"]
        for item in data["diff"]:
            rows[item["f14"]] = (item["f12"], item["f14"])
        if len(rows) >= data["total"]:
            break
    return rows


def select_symbols(industry_lookup: dict[str, tuple[str, str]], per_industry: int) -> dict[str, dict[str, str]]:
    selected: dict[str, dict[str, str]] = {}
    for theme, industry_names in TARGET_INDUSTRIES:
        for industry_name in industry_names:
            if industry_name not in industry_lookup:
                continue
            code, canonical_name = industry_lookup[industry_name]
            for item in fetch_constituents(code)[:per_industry]:
                stock_code = str(item["code"]).zfill(6)
                selected.setdefault(
                    stock_code,
                    {
                        "name": item["name"],
                        "industry": canonical_name,
                        "theme": theme,
                    },
                )
            time.sleep(0.05)
    return selected


def fetch_constituents(industry_code: str) -> list[dict[str, object]]:
    url = "https://29.push2.eastmoney.com/api/qt/clist/get"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/center/boardlist.html"}
    params = {
        "pn": 1,
        "pz": 100,
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f6",
        "fs": f"b:{industry_code} f:!50",
        "fields": "f12,f14,f6",
    }
    data = requests.get(url, params=params, headers=headers, timeout=20).json()["data"]
    rows = [
        {
            "code": item["f12"],
            "name": item["f14"],
            "amount": to_float(item.get("f6")),
        }
        for item in data["diff"]
    ]
    return sorted(rows, key=lambda item: item["amount"], reverse=True)


def to_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fetch_daily_and_securities(selected: dict[str, dict[str, str]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    import akshare as ak

    daily_frames = []
    securities = []
    for code, meta in selected.items():
        try:
            raw = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date="20260101",
                end_date="20260630",
                adjust="",
            )
            if raw.empty:
                continue
            daily = raw.rename(
                columns={
                    "日期": "date",
                    "开盘": "open",
                    "最高": "high",
                    "最低": "low",
                    "收盘": "close",
                    "成交量": "volume",
                    "成交额": "turnover_amount",
                    "换手率": "turnover_rate",
                }
            )
            daily["code"] = code
            daily_frames.append(
                daily[["date", "code", "open", "high", "low", "close", "volume", "turnover_amount", "turnover_rate"]]
            )
            securities.append(
                {
                    "code": code,
                    "name": meta["name"],
                    "industry": meta["industry"],
                    "listing_date": "1900-01-01",
                    "is_st": "ST" in meta["name"].upper(),
                    "delisting_risk": "退" in meta["name"],
                }
            )
        except Exception as exc:  # noqa: BLE001
            print(f"skip {code}: {exc}", file=sys.stderr)
        time.sleep(0.03)
    if not daily_frames:
        raise RuntimeError("没有成功拉取任何行情。")
    return pd.concat(daily_frames, ignore_index=True), pd.DataFrame(securities)


def build_fallback_watchlist(raw: pd.DataFrame) -> pd.DataFrame:
    latest_date = raw["date"].max()
    latest = raw[raw["date"] == latest_date].copy()
    latest = latest.sort_values("turnover_amount", ascending=False).head(30)
    return pd.DataFrame(
        {
            "股票代码": latest["code"].astype(str).str.zfill(6),
            "股票名称": latest["name"],
            "所属行业": latest["industry"],
            "触发条件": "处于重点趋势行业；成交额相对靠前",
            "风险提示": "未完全满足技术筛选条件，仅作为行业观察样本",
            "建议动作": "等待回调",
        }
    )


def build_trend_snapshot(raw: pd.DataFrame, watchlist: pd.DataFrame) -> pd.DataFrame:
    rows = []
    watch_codes = set(watchlist["股票代码"].astype(str).str.zfill(6))
    for code, group in raw.sort_values("date").groupby("code"):
        code = str(code).zfill(6)
        if code not in watch_codes:
            continue
        if len(group) < 21:
            continue
        latest = group.iloc[-1]
        close = float(latest["close"])
        close_5 = float(group.iloc[-6]["close"]) if len(group) >= 6 else close
        close_20 = float(group.iloc[-21]["close"]) if len(group) >= 21 else close
        close_60 = float(group.iloc[-61]["close"]) if len(group) >= 61 else close
        ma20 = float(group["close"].tail(20).mean())
        amount_ma20 = float(group["turnover_amount"].tail(20).mean())
        amount_ratio = float(latest["turnover_amount"]) / amount_ma20 if amount_ma20 else 0
        gain_5 = close / close_5 - 1 if close_5 else 0
        gain_20 = close / close_20 - 1 if close_20 else 0
        gain_60 = close / close_60 - 1 if close_60 else 0
        score = trend_score(gain_20, close / ma20 - 1 if ma20 else 0, amount_ratio)
        rows.append(
            {
                "股票代码": code,
                "股票名称": latest["name"],
                "所属行业": latest["industry"],
                "近5日涨幅": gain_5,
                "近20日涨幅": gain_20,
                "近60日涨幅": gain_60,
                "成交额放大倍数": amount_ratio,
                "收盘价相对20日均线": close / ma20 - 1 if ma20 else 0,
                "趋势图标分": score,
            }
        )
    snapshot = pd.DataFrame(rows)
    if snapshot.empty:
        return snapshot
    return snapshot.sort_values(["趋势图标分", "近20日涨幅", "成交额放大倍数"], ascending=False).reset_index(drop=True)


def trend_score(gain_20: float, close_vs_ma20: float, amount_ratio: float) -> int:
    score = 0
    if gain_20 > 0:
        score += 35
    if close_vs_ma20 > 0:
        score += 35
    if amount_ratio > 1.2:
        score += 30
    return score


if __name__ == "__main__":
    main()
