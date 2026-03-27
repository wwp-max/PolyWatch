# core_analysis — 数据访问与质量分析模块

> 最后更新：2026-03-08

本模块为所有团队成员提供统一的数据库查询接口和数据质量分析工具。

---

## 目录

- [DB 接口（db_interface.py）](#db-接口db_interfacepy)
- [数据质量报告（data_quality.py）](#数据质量报告data_qualitypy)
- [CLI 使用](#cli-使用)
- [测试](#测试)

---

## DB 接口（db_interface.py）

供其他成员（C、D、E）通过 Python 代码直接查询 TimescaleDB。

### 连接方式

```python
from db_interface import *
# 自动读取 DATABASE_URL 环境变量，默认 localhost:5433
```

### 可用函数

#### 读取价格数据（Member C 算法使用）

```python
import pandas as pd
from db_interface import get_price_series

# 获取完整价格序列
df = get_price_series("presidential-election-winner-2024")
# df: DataFrame, index=time, columns=[price]

# 只获取指定日期之后的数据
df = get_price_series("presidential-election-winner-2024", since="2024-10-01")
```

#### 获取市场列表（Member E Dashboard 使用）

```python
from db_interface import get_markets_df

markets_df = get_markets_df()
# columns: slug, question, active, last_price, prev_price
# 匹配前端 TypeScript Market 类型
```

#### 写入异常事件（Member C 跑算法后写入）

```python
from db_interface import write_anomaly, get_token_id_by_slug
from datetime import datetime, timezone

token_id = get_token_id_by_slug("what-will-happen-before-gta-vi")
write_anomaly(
    token_id=token_id,
    detected_at=datetime.now(timezone.utc),
    event_type="zscore_spike",
    severity="high",
    detail={"z_score": 4.2, "price": 0.87, "market_slug": "what-will-happen-before-gta-vi"}
)
```

#### 查询异常事件（Member E Dashboard 使用）

```python
from db_interface import query_anomalies

# 获取全部异常
df = query_anomalies()
# columns: id, marketSlug, detectedAt, eventType, severity, detail

# 按市场筛选
df = query_anomalies(slug="presidential-election-winner-2024")

# 按严重度筛选
df = query_anomalies(severity="high")
```

#### 市场统计（Member B 数据质量使用）

```python
from db_interface import get_market_stats, get_active_slugs, get_data_gaps

# 获取所有市场的统计信息
stats = get_market_stats()
# [{slug, question, row_count, first_time, last_time, avg_price}, ...]

# 获取有数据的市场 slug 列表
slugs = get_active_slugs()

# 检测时间序列中的缺失区间
gaps = get_data_gaps("presidential-election-winner-2024")
# [{gap_start, gap_end, gap_hours}, ...]
```

---

## 数据质量报告（data_quality.py）

自动生成数据质量分析报告，检测完整性、时效性、越界数据等。

### 使用方式

```python
from data_quality import generate_report, format_markdown

# 生成报告
report = generate_report()
# report: {generated_at, summary, markets, orphan_markets}

# 转为 markdown
md = format_markdown(report)
print(md)
```

### 健康度分级

| 状态 | 条件 |
|------|------|
| **healthy** | 完整性 ≥ 95%，数据 < 2h，无越界价格 |
| **degraded** | 完整性 85-95%，或数据 2-12h 旧 |
| **critical** | 完整性 < 85%，或数据 > 12h，或含越界价格 |
| **closed** | 数据 > 90 天旧（市场已结束） |

---

## CLI 使用

```bash
# Markdown 格式输出到终端
python core_analysis/run_quality_report.py

# 保存为文件
python core_analysis/run_quality_report.py -o docs/data-quality-report.md

# JSON 格式（供 API 消费）
python core_analysis/run_quality_report.py -f json
```

---

## 测试

### 运行所有测试

```bash
cd PolyWatch
source /path/to/venv/bin/activate
DATABASE_URL=postgresql://polywatch:polywatch@localhost:5433/polywatch \
pytest tests/core_analysis/ -v
```

### 测试覆盖（25 个）

| 模块 | 数量 | 类型 |
|------|------|------|
| `test_db_interface.py` | 12 | 单元测试（mocked DB） |
| `test_data_quality.py` | 8 | 单元测试（mocked DB 接口） |
| `test_e2e.py` | 5 | 集成测试（真实 DB） |

---

## 与其他模块的关系

| 成员 | 使用方式 |
|------|----------|
| **C**（算法） | `get_price_series(slug)` → 跑 Z-Score/Whale → `write_anomaly()` |
| **D**（取证） | `get_price_series(slug)` 替代直接读 CSV |
| **E**（前端） | FastAPI 包装 `get_markets_df()`、`get_price_series()`、`query_anomalies()` → 匹配前端 TypeScript 类型 |
| **B**（数据） | `generate_report()` + `get_data_gaps()` 监控数据质量 |
