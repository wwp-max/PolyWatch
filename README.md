# PolyWatch

**PolyWatch** 是一个面向 Polymarket 预测市场的市场完整性监测系统，用于检测价格操纵、异常波动及可疑交易行为。

> Course: CS6290 Privacy-Enhancing Technologies | Group 16

---

## 快速启动

```bash
git clone https://github.com/wwp-max/PolyWatch.git
cd PolyWatch/data_pipeline
docker compose up -d
docker compose logs -f collector
```

**首次启动需导入种子数据：** Collector 自动回溯30天。对于已结束的市场（如 2024 大选），必须手动导入 `db/price_history_seed.csv`。详见 [`data_pipeline/README.md`](data_pipeline/README.md) 第 3 节。

### 前置条件

- Docker Desktop（含 WSL2 集成）
- Python 3.10+

---

## 数据库连接

| 项 | 值 |
|---|---|
| Host | `localhost` |
| Port | **5433**（不是默认 5432） |
| Database | `polywatch` |
| User | `polywatch` |
| Password | `polywatch` |

```python
# Python 直接连接
import psycopg2
conn = psycopg2.connect("postgresql://polywatch:polywatch@localhost:5433/polywatch")
```

DBeaver、psql 等工具均可使用上述连接。

---

## 当前数据

| 市场 | 用途 | 数据量 | 状态 |
|------|------|--------|------|
| `presidential-election-winner-2024` | 算法回测 | 7,356 条（2024-01-05 ~ 2024-11-06）| 已结束 |
| `what-will-happen-before-gta-vi` | 实时监控 | ~780 条 | 持续更新 |
| `will-trump-acquire-greenland-before-2027` | 实时监控 | ~770 条 | 持续更新 |
| `fed-decision-in-march-885` | 元数据 | 720 条 | — |
| `presidential-election-winner-2028` | 元数据 | 331 条 | — |
| `democratic-presidential-nominee-2028` | 元数据 | 719 条 | — |

---

## 数据相关模块

### data_pipeline

自动化数据采集管道，每 5 分钟从 Polymarket CLOB API 拉取价格数据，写入 TimescaleDB。
详见 [`data_pipeline/README.md`](data_pipeline/README.md)。

### core_analysis / db_interface

共享 DB 读写接口，供所有成员使用：

```python
from core_analysis.db_interface import get_price_series, write_anomaly, query_anomalies

# 读取价格序列
df = get_price_series("presidential-election-winner-2024")

# 写入异常事件
write_anomaly(token_id, datetime.now(), "zscore_spike", "high", {"z_score": 4.2})

# 查询异常事件
anomalies = query_anomalies(slug="presidential-election-winner-2024")
```

完整文档见 [`core_analysis/README.md`](core_analysis/README.md)。

### 数据质量报告

```bash
python core_analysis/run_quality_report.py
```

---

## 运行测试

```bash
source venv/bin/activate
DATABASE_URL=postgresql://polywatch:polywatch@localhost:5433/polywatch \
pytest tests/ -v
```

预期：**38 passed**（data_pipeline 13 + core_analysis 25）
