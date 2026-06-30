from __future__ import annotations

import pandas as pd

from .compliance import validate_action
from .config import ScreeningConfig


REPORT_COLUMNS = ["股票代码", "股票名称", "所属行业", "触发条件", "风险提示", "建议动作"]


def build_watchlist(raw: pd.DataFrame, config: ScreeningConfig) -> pd.DataFrame:
    df = raw.copy()
    if config.as_of_date:
        as_of = pd.to_datetime(config.as_of_date)
        df = df[df["date"] <= as_of]
    else:
        as_of = df["date"].max()

    metrics = _add_metrics(df, config)
    latest = metrics[metrics["date"] == as_of].copy()
    if latest.empty:
        raise ValueError(f"没有找到截至 {as_of.date()} 的行情数据")

    report_rows = []
    for row in latest.itertuples(index=False):
        stock_name = str(row.name)
        exclusion_reasons = _base_exclusion_reasons(row, as_of, config)
        trigger_flags = {
            "20日均线向上": bool(row.ma20_up),
            "收盘价站上20日均线": bool(row.close_above_ma20),
            f"成交额大于20日均值{config.amount_spike_multiple:.1f}倍": bool(row.amount_spike),
            "近5日涨幅不超过25%": bool(row.gain_5d_ok),
            "换手率在合理区间": bool(row.turnover_ok),
        }

        if exclusion_reasons:
            action = "排除"
            risk = "；".join(exclusion_reasons)
        elif all(trigger_flags.values()):
            action = "观察"
            risk = _risk_note(row)
        else:
            action = "等待回调"
            failed = [name for name, passed in trigger_flags.items() if not passed]
            risk = "未完全满足：" + "；".join(failed)

        validate_action(action)
        report_rows.append(
            {
                "股票代码": str(row.code).zfill(6),
                "股票名称": stock_name,
                "所属行业": row.industry,
                "触发条件": "；".join(name for name, passed in trigger_flags.items() if passed) or "无",
                "风险提示": risk,
                "建议动作": action,
                "_rank_amount_ratio": row.amount_ratio,
                "_rank_turnover": row.turnover_rate,
            }
        )

    report = pd.DataFrame(report_rows)
    report = report[report["建议动作"].isin(["观察", "等待回调"])]
    report = report.sort_values(
        by=["建议动作", "_rank_amount_ratio", "_rank_turnover"],
        ascending=[True, False, True],
    )
    return report[REPORT_COLUMNS].reset_index(drop=True)


def _add_metrics(df: pd.DataFrame, config: ScreeningConfig) -> pd.DataFrame:
    out = df.sort_values(["code", "date"]).copy()
    group = out.groupby("code", group_keys=False)
    out["ma20"] = group["close"].transform(lambda s: s.rolling(config.ma_window).mean())
    out["ma20_prev"] = group["ma20"].shift(1)
    out["amount_ma20"] = group["turnover_amount"].transform(lambda s: s.rolling(config.ma_window).mean())
    out["close_5d_ago"] = group["close"].shift(5)
    out["gain_5d"] = out["close"] / out["close_5d_ago"] - 1
    out["listing_days"] = (out["date"] - out["listing_date"]).dt.days

    out["ma20_up"] = out["ma20"] > out["ma20_prev"]
    out["close_above_ma20"] = out["close"] > out["ma20"]
    out["amount_ratio"] = out["turnover_amount"] / out["amount_ma20"]
    out["amount_spike"] = out["amount_ratio"] > config.amount_spike_multiple
    out["gain_5d_ok"] = out["gain_5d"] <= config.max_5d_gain
    out["turnover_ok"] = out["turnover_rate"].between(config.min_turnover, config.max_turnover, inclusive="both")
    return out


def _base_exclusion_reasons(row: object, as_of: pd.Timestamp, config: ScreeningConfig) -> list[str]:
    reasons: list[str] = []
    name = str(row.name).upper()
    if bool(row.is_st) or "ST" in name or "*ST" in name:
        reasons.append("ST或特殊处理标的")
    if bool(row.delisting_risk) or "退" in str(row.name):
        reasons.append("存在退市风险标识")
    if row.turnover_amount < config.min_amount:
        reasons.append("成交额低于阈值")
    if row.listing_days < config.min_listing_days:
        reasons.append("上市时间过短")
    if pd.isna(row.ma20) or pd.isna(row.ma20_prev) or pd.isna(row.amount_ma20) or pd.isna(row.close_5d_ago):
        reasons.append("历史数据不足")
    return reasons


def _risk_note(row: object) -> str:
    notes = ["仅作为观察名单，不构成交易建议"]
    if row.gain_5d > 0.18:
        notes.append("近5日涨幅偏高，注意短线波动")
    if row.turnover_rate > 12:
        notes.append("换手率较高，注意情绪波动")
    if row.amount_ratio > 3:
        notes.append("成交额明显放大，需观察持续性")
    return "；".join(notes)
