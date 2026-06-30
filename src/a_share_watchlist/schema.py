from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Set


@dataclass(frozen=True)
class TableSchema:
    name: str
    required: Set[str]
    optional: Set[str]
    aliases: Dict[str, str]

    @property
    def all_known(self) -> Set[str]:
        return self.required | self.optional


DAILY_BARS_SCHEMA = TableSchema(
    name="daily_bars",
    required={
        "date",
        "code",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "turnover_amount",
        "turnover_rate",
    },
    optional={
        "pre_close",
        "adj_factor",
        "vwap",
        "limit_up",
        "limit_down",
        "suspended",
    },
    aliases={
        "trade_date": "date",
        "ts_code": "code",
        "symbol": "code",
        "股票代码": "code",
        "日期": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "turnover_amount",
        "换手率": "turnover_rate",
    },
)

SECURITIES_SCHEMA = TableSchema(
    name="securities",
    required={
        "code",
        "name",
        "industry",
        "listing_date",
        "is_st",
        "delisting_risk",
    },
    optional={
        "exchange",
        "market",
        "board",
        "status",
        "area",
    },
    aliases={
        "ts_code": "code",
        "symbol": "code",
        "股票代码": "code",
        "股票名称": "name",
        "名称": "name",
        "行业": "industry",
        "所属行业": "industry",
        "上市日期": "listing_date",
        "是否ST": "is_st",
        "退市风险": "delisting_risk",
    },
)


def normalize_columns(columns: Iterable[str], aliases: Dict[str, str]) -> Dict[str, str]:
    return {column: aliases.get(column, column) for column in columns}
