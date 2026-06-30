# A 股候选股票筛选助手

这是一个只输出“观察名单”的 Python 项目，不做自动交易，不输出买入、卖出、目标价或仓位建议。

## 功能

- 支持导入每日 A 股历史行情 CSV。
- 过滤 ST、退市风险、成交额过低、上市时间过短的股票。
- 筛选条件：
  - 20 日均线向上；
  - 收盘价站上 20 日均线；
  - 当日成交额大于过去 20 日均值的 1.5 倍；
  - 近 5 日涨幅不超过 25%；
  - 换手率在合理区间。
- 输出 Excel 报告。
- 建议动作仅允许：观察、等待回调、排除。

## 项目结构

```text
a_share_watchlist_assistant/
  README.md
  pyproject.toml
  requirements.txt
  sample_data/
    daily_bars.csv
    daily_prices.csv
    securities.csv
  src/
    a_share_watchlist/
      __init__.py
      cli.py
      compliance.py
      config.py
      data_loader.py
      report.py
      schema.py
      screener.py
  tests/
    test_compliance.py
    test_screener.py
```

## 安装方式

建议使用虚拟环境：

```bash
cd /Users/arosy/Documents/Codex/2026-06-30/100/outputs/a_share_watchlist_assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install .
```

如果希望程序自己联网拉公开行情数据，再安装 AkShare：

```bash
pip install -r requirements-akshare.txt
```

## 成熟交易数据模式

推荐使用“两张表”的模式：

1. `daily_bars.csv`：日线行情事实表，按 `date + code` 唯一。
2. `securities.csv`：证券主数据表，按 `code` 唯一。

这样做的好处是行情数据可以每天追加，名称、行业、上市日期、ST、退市风险等静态或低频字段单独维护。以后接 AkShare、Tushare、BaoStock、券商导出或本地数据库时，只需要映射到这两张表。

### daily_bars.csv

| 字段 | 含义 | 示例 |
|---|---|---|
| date | 交易日期 | 2026-06-30 |
| code | 股票代码 | 600000 |
| open | 开盘价 | 10.10 |
| high | 最高价 | 10.80 |
| low | 最低价 | 10.02 |
| close | 收盘价 | 10.52 |
| volume | 成交量，建议用手数 | 3920000 |
| turnover_amount | 成交额，单位元 | 530000000 |
| turnover_rate | 换手率，百分数数值 | 3.2 |

可选字段：

- `pre_close`
- `adj_factor`
- `vwap`
- `limit_up`
- `limit_down`
- `suspended`

### securities.csv

| 字段 | 含义 | 示例 |
|---|---|---|
| code | 股票代码 | 600000 |
| name | 股票名称 | 示例银行 |
| industry | 所属行业 | 银行 |
| listing_date | 上市日期 | 2010-01-01 |
| is_st | 是否 ST | false |
| delisting_risk | 是否有退市风险 | false |

可选字段：

- `exchange`
- `market`
- `board`
- `status`
- `area`

### 字段别名

程序支持一些常见中文字段名和接口字段名的自动映射，例如：

- `trade_date` -> `date`
- `ts_code` / `symbol` / `股票代码` -> `code`
- `开盘` -> `open`
- `最高` -> `high`
- `最低` -> `low`
- `收盘` -> `close`
- `成交量` -> `volume`
- `成交额` -> `turnover_amount`
- `换手率` -> `turnover_rate`
- `股票名称` / `名称` -> `name`
- `所属行业` / `行业` -> `industry`
- `上市日期` -> `listing_date`
- `是否ST` -> `is_st`
- `退市风险` -> `delisting_risk`

## 兼容旧版合并 CSV

CSV 需要是一张“多股票、多交易日”的历史行情表，每行代表一只股票在一个交易日的数据。

必需字段：

| 字段 | 含义 | 示例 |
|---|---|---|
| date | 交易日期 | 2026-06-30 |
| code | 股票代码 | 600000 |
| name | 股票名称 | 示例银行 |
| industry | 所属行业 | 银行 |
| close | 收盘价 | 10.52 |
| turnover_amount | 成交额，单位元 | 530000000 |
| turnover_rate | 换手率，百分数数值 | 3.2 |
| listing_date | 上市日期 | 2010-01-01 |
| is_st | 是否 ST | false |
| delisting_risk | 是否有退市风险 | false |

## 运行方式

使用样例数据生成报告：

```bash
python sample_data/generate_sample_data.py
python -m a_share_watchlist.cli \
  --input sample_data/daily_bars.csv \
  --securities sample_data/securities.csv \
  --output outputs/watchlist_report.xlsx
```

联网拉取指定股票并生成报告：

```bash
python -m a_share_watchlist.cli \
  --provider akshare \
  --symbols 600000,000001,300750 \
  --start-date 2026-01-01 \
  --end-date 2026-06-30 \
  --output outputs/watchlist_report_akshare.xlsx
```

联网模式默认会尝试使用东方财富行业板块补全行业字段。公开接口偶尔会限流或断开，程序会重试；如果仍失败，会保留 `未知` 并继续生成报告。

只测试少量东方财富行业板块：

```bash
python -m a_share_watchlist.cli \
  --provider akshare \
  --symbols 600000,000001,300750 \
  --start-date 2026-01-01 \
  --end-date 2026-06-30 \
  --industry-limit 20 \
  --output outputs/watchlist_report_akshare.xlsx
```

首次试全市场时建议先限制数量，避免拉取过慢：

```bash
python -m a_share_watchlist.cli \
  --provider akshare \
  --start-date 2026-01-01 \
  --end-date 2026-06-30 \
  --max-symbols 100 \
  --output outputs/watchlist_report_akshare.xlsx
```

自定义阈值：

```bash
python -m a_share_watchlist.cli \
  --input /path/to/daily_bars.csv \
  --securities /path/to/securities.csv \
  --output outputs/watchlist_report.xlsx \
  --min-amount 100000000 \
  --min-listing-days 180 \
  --min-turnover 1 \
  --max-turnover 20
```

更宽松的自用观察参数示例：

```bash
python -m a_share_watchlist.cli \
  --input /path/to/daily_bars.csv \
  --securities /path/to/securities.csv \
  --output outputs/watchlist_report.xlsx \
  --min-amount 50000000 \
  --min-listing-days 90 \
  --min-turnover 0.5 \
  --max-turnover 35 \
  --amount-spike-multiple 1.2 \
  --max-5d-gain 0.35
```

## 报告字段

Excel 的 `观察名单` sheet 包含：

- 股票代码
- 股票名称
- 所属行业
- 触发条件
- 风险提示
- 建议动作

Excel 的 `参数` sheet 记录本次筛选阈值。

## 合规边界

本项目只做候选观察名单，不做交易建议。报告中的建议动作只能是：

- 观察
- 等待回调
- 排除

代码默认会扫描输出文本，禁止出现以下措辞，避免把观察名单变成交易指令：

- 买入
- 卖出
- 满仓
- 目标价
- 加仓
- 减仓
- 建仓
- 清仓

## 数据源说明

当前版本优先支持本地 CSV，适合接入你已有的行情导出、量化数据库或公开接口下载后的文件。后续可以在 `data_loader.py` 中增加 AkShare、BaoStock、Tushare 等公开行情接口适配器，但建议保持同一套字段格式，避免影响筛选逻辑。

当前也支持 AkShare 公开接口作为可选数据源。公开接口可能因为源站、限流、字段变化而失败，所以 CSV 模式仍然保留为稳定兜底。
