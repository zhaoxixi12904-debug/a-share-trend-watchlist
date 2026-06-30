from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from .schema import DAILY_BARS_SCHEMA, SECURITIES_SCHEMA, normalize_columns

LEGACY_REQUIRED_COLUMNS = {
    "date",
    "code",
    "name",
    "industry",
    "close",
    "turnover_amount",
    "turnover_rate",
    "listing_date",
    "is_st",
    "delisting_risk",
}


def load_daily_csv(path: str | Path, securities_path: Optional[str | Path] = None) -> pd.DataFrame:
    daily = load_daily_bars_csv(path)
    if securities_path:
        securities = load_securities_csv(securities_path)
        return merge_daily_with_securities(daily, securities)

    missing_legacy = LEGACY_REQUIRED_COLUMNS - set(daily.columns)
    if missing_legacy:
        raise ValueError(
            "行情 CSV 缺少证券主数据字段。请传入 --securities，或使用兼容旧格式的合并 CSV。"
            f" 缺少字段：{', '.join(sorted(missing_legacy))}"
        )
    return _normalize_combined(daily)


def load_daily_bars_csv(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"CSV 文件不存在：{source}")

    df = pd.read_csv(source, dtype={"code": str})
    df = df.rename(columns=normalize_columns(df.columns, DAILY_BARS_SCHEMA.aliases))

    # Backward compatibility: the first project version did not require OHLCV.
    for column in ("open", "high", "low"):
        if column not in df.columns and "close" in df.columns:
            df[column] = df["close"]
    if "volume" not in df.columns:
        df["volume"] = 0

    missing = {"date", "code", "close", "turnover_amount", "turnover_rate"} - set(df.columns)
    if missing:
        raise ValueError(f"行情 CSV 缺少必需字段：{', '.join(sorted(missing))}")

    df = df.copy()
    df["code"] = df["code"].str.zfill(6)
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    for column in ("open", "high", "low", "close", "volume", "turnover_amount", "turnover_rate"):
        df[column] = pd.to_numeric(df[column], errors="raise")

    return df.sort_values(["code", "date"]).reset_index(drop=True)


def load_securities_csv(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"证券主数据 CSV 不存在：{source}")

    df = pd.read_csv(source, dtype={"code": str})
    df = df.rename(columns=normalize_columns(df.columns, SECURITIES_SCHEMA.aliases))
    missing = SECURITIES_SCHEMA.required - set(df.columns)
    if missing:
        raise ValueError(f"证券主数据 CSV 缺少必需字段：{', '.join(sorted(missing))}")

    df = df.copy()
    df["code"] = df["code"].str.zfill(6)
    df["listing_date"] = pd.to_datetime(df["listing_date"], errors="raise")
    df["is_st"] = df["is_st"].map(_to_bool)
    df["delisting_risk"] = df["delisting_risk"].map(_to_bool)
    return df.drop_duplicates("code", keep="last").reset_index(drop=True)


def merge_daily_with_securities(daily: pd.DataFrame, securities: pd.DataFrame) -> pd.DataFrame:
    merged = daily.merge(securities, on="code", how="left", validate="many_to_one")
    missing_master = merged[merged["name"].isna()]["code"].drop_duplicates().tolist()
    if missing_master:
        sample = ", ".join(missing_master[:10])
        raise ValueError(f"证券主数据缺少以下股票代码：{sample}")
    return _normalize_combined(merged)


def _normalize_combined(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["code"] = out["code"].astype(str).str.zfill(6)
    out["date"] = pd.to_datetime(out["date"], errors="raise")
    out["listing_date"] = pd.to_datetime(out["listing_date"], errors="raise")
    for column in ("close", "turnover_amount", "turnover_rate"):
        out[column] = pd.to_numeric(out[column], errors="raise")
    out["is_st"] = out["is_st"].map(_to_bool)
    out["delisting_risk"] = out["delisting_risk"].map(_to_bool)
    return out.sort_values(["code", "date"]).reset_index(drop=True)


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "t", "yes", "y", "是", "st", "risk"}
