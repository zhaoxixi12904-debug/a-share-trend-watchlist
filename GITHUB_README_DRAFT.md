# A Share Trend Watchlist

一个面向 A 股的趋势观察名单生成器。

它可以自动拉取公开行情数据，匹配东方财富行业分类，结合行业趋势判断和技术筛选条件，生成带图表的 Excel 观察报告。

## 能做什么

- 拉取 A 股日线行情；
- 匹配东方财富行业；
- 根据政策和产业趋势构建重点行业股票池；
- 筛选 20 日均线、成交额放大、近 5 日涨幅、换手率；
- 输出 Excel；
- 生成走势概览图表。

## 不做什么

- 不做自动交易；
- 不输出买入建议；
- 不输出卖出建议；
- 不给目标价；
- 不承诺收益。

## 示例报告

报告包含：

- 行业判断；
- 走势概览；
- 观察名单。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-akshare.txt
PYTHONPATH=src python scripts/build_trend_watchlist.py
```

输出文件：

```text
outputs/trend_watchlist_2026.xlsx
```

## 付费定制

如果你不想自己部署，可以定制报告：

- 每周趋势观察报告；
- 指定行业观察名单；
- 私有化部署；
- 自定义数据源。

报告只做数据整理和观察名单，不构成交易建议。
