from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import time
from typing import Iterable, Optional

import pandas as pd
import requests

from .data_loader import merge_daily_with_securities


@dataclass(frozen=True)
class AkshareFetchConfig:
    start_date: str
    end_date: str
    symbols: Optional[list[str]] = None
    max_symbols: Optional[int] = None
    adjust: str = ""
    industry_source: str = "eastmoney"
    industry_limit: Optional[int] = None


def fetch_akshare_daily(config: AkshareFetchConfig) -> pd.DataFrame:
    ak = _import_akshare()
    code_name_map = _fetch_akshare_code_name_map(ak)
    symbols = config.symbols or list(code_name_map.keys())
    if config.max_symbols:
        symbols = symbols[: config.max_symbols]
    if not symbols:
        raise ValueError("没有可拉取的股票代码，请使用 --symbols 指定。")
    symbols = [_normalize_symbol(symbol) for symbol in symbols]
    industry_map = (
        _fetch_eastmoney_industry_map(config, set(symbols))
        if config.industry_source == "eastmoney"
        else {}
    )

    daily_frames = []
    security_rows = []
    failures = []
    for symbol in symbols:
        code = _normalize_symbol(symbol)
        try:
            daily_frames.append(_fetch_one_daily_bar(ak, code, config))
            security_rows.append(
                _fetch_one_security(
                    ak,
                    code,
                    code_name_map.get(code, code),
                    industry_map.get(code, "未知"),
                )
            )
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{code}: {exc}")

    if not daily_frames:
        raise RuntimeError("AkShare 没有成功返回任何日线数据。失败信息：" + " | ".join(failures[:5]))

    daily = pd.concat(daily_frames, ignore_index=True)
    securities = pd.DataFrame(security_rows).drop_duplicates("code", keep="last")
    return merge_daily_with_securities(daily, securities)


def _import_akshare():
    try:
        import akshare as ak  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "当前环境没有安装 akshare。请运行：pip install -r requirements-akshare.txt"
        ) from exc
    return ak


def _fetch_akshare_code_name_map(ak) -> dict[str, str]:
    code_name = ak.stock_info_a_code_name()
    code_col = _pick_column(code_name, ["code", "代码", "股票代码"])
    name_col = _pick_column(code_name, ["name", "名称", "股票名称"])
    return {
        _normalize_symbol(row[code_col]): str(row[name_col])
        for _, row in code_name.iterrows()
    }


def _fetch_one_daily_bar(ak, code: str, config: AkshareFetchConfig) -> pd.DataFrame:
    raw = ak.stock_zh_a_hist(
        symbol=code,
        period="daily",
        start_date=_compact_date(config.start_date),
        end_date=_compact_date(config.end_date),
        adjust=config.adjust,
    )
    if raw.empty:
        raise ValueError("日线数据为空")

    columns = {
        "日期": "date",
        "股票代码": "code",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "turnover_amount",
        "换手率": "turnover_rate",
    }
    df = raw.rename(columns=columns)
    df["code"] = code
    required = ["date", "code", "open", "high", "low", "close", "volume", "turnover_amount", "turnover_rate"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("AkShare 日线字段缺失：" + ", ".join(missing))
    return df[required]


def _fetch_eastmoney_industry_map(config: AkshareFetchConfig, target_codes: set[str]) -> dict[str, str]:
    try:
        industries = _fetch_eastmoney_industry_list_direct()
    except Exception:
        return {}

    names = [
        (str(row["industry_code"]), str(row["industry_name"]))
        for _, row in industries.iterrows()
    ]
    if config.industry_limit:
        names = names[: config.industry_limit]

    mapping: dict[str, str] = {}
    for industry_code, industry_name in names:
        try:
            cons = _fetch_eastmoney_industry_constituents_direct(industry_code)
        except Exception:
            continue
        for code in cons["code"].dropna().tolist():
            mapping.setdefault(_normalize_symbol(code), industry_name)
        if target_codes and target_codes.issubset(mapping.keys()):
            break
        time.sleep(0.05)
    return mapping


def _fetch_eastmoney_industry_list_direct() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    page = 1
    page_size = 100
    while True:
        data = _eastmoney_clist(
            host="17.push2.eastmoney.com",
            params={
                "pn": page,
                "pz": page_size,
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:90 t:2 f:!50",
                "fields": "f12,f14",
            },
        )
        diff = data.get("diff") or []
        rows.extend(
            {"industry_code": item.get("f12"), "industry_name": item.get("f14")}
            for item in diff
            if item.get("f12") and item.get("f14")
        )
        total = int(data.get("total") or len(rows))
        if len(rows) >= total or not diff:
            break
        page += 1
    return pd.DataFrame(rows).drop_duplicates("industry_code", keep="last")


def _fetch_eastmoney_industry_constituents_direct(industry_code: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    page = 1
    page_size = 100
    while True:
        data = _eastmoney_clist(
            host="29.push2.eastmoney.com",
            params={
                "pn": page,
                "pz": page_size,
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": f"b:{industry_code} f:!50",
                "fields": "f12,f14",
            },
        )
        diff = data.get("diff") or []
        rows.extend(
            {"code": item.get("f12"), "name": item.get("f14")}
            for item in diff
            if item.get("f12")
        )
        total = int(data.get("total") or len(rows))
        if len(rows) >= total or not diff:
            break
        page += 1
    return pd.DataFrame(rows)


def _eastmoney_clist(host: str, params: dict[str, object]) -> dict[str, object]:
    url = f"https://{host}/api/qt/clist/get"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://quote.eastmoney.com/center/boardlist.html",
    }
    response = _request_with_retries(url, params=params, headers=headers)
    payload = response.json()
    if payload.get("rc") != 0 or not payload.get("data"):
        raise RuntimeError(f"东方财富接口返回异常：{payload}")
    return payload["data"]


def _request_with_retries(url: str, retries: int = 3, delay: float = 0.8, **kwargs):
    last_error: Optional[Exception] = None
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=20, **kwargs)
            response.raise_for_status()
            return response
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    raise RuntimeError(str(last_error))


def _call_with_retries(func, retries: int = 3, delay: float = 0.8, **kwargs):
    last_error: Optional[Exception] = None
    for attempt in range(retries):
        try:
            return func(**kwargs)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    raise RuntimeError(str(last_error))


def _fetch_one_security(ak, code: str, fallback_name: str, fallback_industry: str) -> dict[str, object]:
    fallback = {
        "code": code,
        "name": fallback_name,
        "industry": fallback_industry,
        "listing_date": "1900-01-01",
        "is_st": False,
        "delisting_risk": False,
    }
    try:
        info = ak.stock_individual_info_em(symbol=code)
    except Exception:  # noqa: BLE001
        fallback["is_st"] = "ST" in fallback_name.upper()
        fallback["delisting_risk"] = "退" in fallback_name
        return fallback

    item_col = _pick_column(info, ["item", "项目"])
    value_col = _pick_column(info, ["value", "值"])
    mapping = dict(zip(info[item_col].astype(str), info[value_col]))
    name = str(mapping.get("股票简称", fallback_name))
    listing_date = _format_listing_date(mapping.get("上市时间", "19000101"))
    return {
        "code": code,
        "name": name,
        "industry": str(mapping.get("行业", fallback_industry)),
        "listing_date": listing_date,
        "is_st": "ST" in name.upper(),
        "delisting_risk": "退" in name,
    }


def _pick_column(df: pd.DataFrame, candidates: Iterable[str]) -> str:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    raise ValueError(f"找不到字段，可选字段：{', '.join(candidates)}；实际字段：{', '.join(map(str, df.columns))}")


def _normalize_symbol(symbol: object) -> str:
    return str(symbol).strip().split(".")[0].zfill(6)


def _compact_date(value: str) -> str:
    return value.replace("-", "")


def _format_listing_date(value: object) -> str:
    text = str(value).strip().replace("-", "")
    if len(text) == 8 and text.isdigit():
        return date(int(text[:4]), int(text[4:6]), int(text[6:8])).isoformat()
    return "1900-01-01"
