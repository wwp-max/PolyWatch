# PolyWatch 数据管道使用手册

> 适用对象：所有组员（算法组、可视化组、取证组）
> 最后更新：2026-03-06

> **克隆仓库后请先阅读第 3 节**，数据库初始数据通过 `db/price_history_seed.csv` 一键导入，无需自己等待抓取。

---

## 目录

1. [整体架构与数据流](#1-整体架构与数据流)
2. [环境依赖与前置条件](#2-环境依赖与前置条件)
3. [首次启动](#3-首次启动)
4. [监控市场配置](#4-监控市场配置)
5. [历史数据回溯（backfill）](#5-历史数据回溯backfill)
6. [数据库结构详解](#6-数据库结构详解)
7. [查询数据库——组员操作指南](#7-查询数据库组员操作指南)
8. [在 Python 代码中使用数据](#8-在-python-代码中使用数据)
9. [日常运维操作](#9-日常运维操作)
10. [运行自动化测试](#10-运行自动化测试)
11. [常见问题排查](#11-常见问题排查)
12. [当前数据库状态（快照）](#12-当前数据库状态快照)

---

## 1. 整体架构与数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                        外部 API                                  │
│                                                                   │
│  Polymarket Gamma API              Polymarket CLOB API            │
│  gamma-api.polymarket.com          clob.polymarket.com            │
│  （市场元数据：slug → token_id）    （价格历史时序数据）             │
└────────────────┬────────────────────────────┬────────────────────┘
                 │ ① resolve_token_id(slug)    │ ② fetch_price_history(token_id)
                 ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   collector 容器（Python）                        │
│                                                                   │
│  main.py         每 5 分钟执行一次 collect_once()                  │
│  ├── fetcher.py  负责 HTTP 请求、数据解析                           │
│  └── db.py       负责幂等写入、增量时间戳管理                         │
└─────────────────────────────┬───────────────────────────────────┘
                              │ ③ INSERT ... ON CONFLICT DO NOTHING
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               TimescaleDB 容器（PostgreSQL 16）                   │
│                                                                   │
│  markets         市场元数据（token_id, slug, question）            │
│  price_history   时序价格表（time, token_id, price）               │
│  anomaly_events  异常事件表（供算法组写入检测结果）                    │
└─────────────────────────────────────────────────────────────────┘
```

### 关键设计决策

| 决策 | 原因 |
|------|------|
| TimescaleDB（基于 PostgreSQL）| 时序数据优化，兼容标准 SQL，组员学习成本低 |
| 宿主机端口 **5433**（非 5432）| 避免与宿主机上可能已安装的 PostgreSQL 冲突 |
| 增量拉取（非全量刷新）| 每次只拉取"上次最新时间戳之后"的数据，节省 API 配额 |
| 分批请求（每批 ≤ 6 天）| CLOB API 拒绝单次请求超过约 7 天的时间跨度 |
| `ON CONFLICT DO NOTHING` | 重启或重跑时不产生重复数据，保证幂等性 |

---

## 2. 环境依赖与前置条件

### 必须安装

| 工具 | 最低版本 | 检查命令 |
|------|---------|---------|
| Docker Desktop / Docker Engine | 24.x | `docker --version` |
| Docker Compose | V2（`docker compose`，非 `docker-compose`）| `docker compose version` |
| Python | 3.10+ | `python3 --version` |

### 不需要

- 本地安装 PostgreSQL（数据库完全运行在 Docker 内）
- Polymarket 账号或 API Key（使用公开端点）
- 任何 pip 包（collector 在容器内自行安装依赖）

---

## 3. 首次启动

> **重要：** Git 只保存代码，不保存数据库内容。数据库的历史数据（特别是2024年大选的7,356条记录）以 CSV 形式保存在 `data_pipeline/db/price_history_seed.csv`，需要在启动后手动导入一次。

### 步骤

```bash
# 1. 进入 data_pipeline 目录
cd PolyWatch/data_pipeline

# 2. 启动所有服务（TimescaleDB + collector）
docker compose up -d

# 3. 等待 timescaledb 变为 healthy（约 10 秒）
docker compose ps

# 4. 导入历史种子数据（只需执行一次）
docker cp db/price_history_seed.csv data_pipeline-timescaledb-1:/tmp/seed.csv
docker compose exec timescaledb psql -U polywatch -d polywatch -c "
-- 先插入 markets 元数据（种子数据依赖这些外键）
INSERT INTO markets (token_id, slug, question) VALUES
  ('21742633143463906290569050155826241533067272736897614950488156847949938836455',
   'presidential-election-winner-2024',
   'Will Donald Trump win the 2024 US Presidential Election?'),
  ('46553455570564517989191023458705371521436514261892866503067981558938998232024',
   'fed-decision-in-march-885',
   'Will the Fed decrease interest rates by 50+ bps after the March 2026 meeting?'),
  ('67028631656597977031363620447645908995417871899828777750494099295092202422178',
   'presidential-election-winner-2028',
   'Will Eric Trump win the 2028 US Presidential Election?'),
  ('60590045489347122735554346200880179420435533609307820342798544098823516727807',
   'democratic-presidential-nominee-2028',
   'Will Stephen A. Smith win the 2028 Democratic presidential nomination?'),
  ('8501497159083948713316135768103773293754490207922884688769443031624417212426',
   'what-will-happen-before-gta-vi',
   'Russia-Ukraine Ceasefire before GTA VI?'),
  ('5161623255678193352839985156330393796378434470119114669671615782853260939535',
   'will-trump-acquire-greenland-before-2027',
   'Will Trump acquire Greenland before 2027?')
ON CONFLICT (token_id) DO NOTHING;
"
docker compose exec timescaledb psql -U polywatch -d polywatch -c "
CREATE TEMP TABLE price_history_import (
    slug  TEXT,
    time  TIMESTAMPTZ,
    price NUMERIC(6,4)
);
COPY price_history_import FROM '/tmp/seed.csv' CSV HEADER;
INSERT INTO price_history (time, token_id, price)
SELECT i.time, m.token_id, i.price
FROM price_history_import i
JOIN markets m USING (slug)
ON CONFLICT (time, token_id) DO NOTHING;
"

# 5. 确认数据已导入
docker compose exec timescaledb psql -U polywatch -d polywatch -c "
SELECT m.slug, COUNT(*) AS 行数 FROM price_history ph JOIN markets m USING (token_id) GROUP BY m.slug;
"

# 6. 查看 collector 实时日志
docker compose logs -f collector
```

导入成功后应看到：

```
           slug                            | 行数
-------------------------------------------+------
 presidential-election-winner-2024         | 7356
 what-will-happen-before-gta-vi            |  724
 fed-decision-in-march-885                 |  720
 democratic-presidential-nominee-2028      |  719
 will-trump-acquire-greenland-before-2027  |  712
 presidential-election-winner-2028         |  331
```

之后 collector 会每 5 分钟自动追加最新数据，无需再次手动操作。

---

## 4. 监控市场配置

### 当前追踪的市场

文件：`data_pipeline/collector/main.py`，第 12–18 行：

```python
TRACKED_MARKETS = [
    # 已结束市场——用于算法回测（2024年美国大选，已存入完整历史数据）
    "presidential-election-winner-2024",
    # 实时监控——地缘政治（俄乌停火，价格 ~0.58，结束于 2026-07）
    "what-will-happen-before-gta-vi",
    # 实时监控——美国政策（特朗普格陵兰，价格 ~0.11，结束于 2026-12）
    "will-trump-acquire-greenland-before-2027",
]
```

### 如何找到新的市场 slug

**方法一：浏览器直接找**

打开 [polymarket.com](https://polymarket.com)，进入任意市场页面，URL 中 `/event/` 后面的部分就是 slug。

例如：`https://polymarket.com/event/will-trump-acquire-greenland-before-2027`
→ slug 为 `will-trump-acquire-greenland-before-2027`

**方法二：API 搜索活跃市场**

```bash
# 按交易量降序列出最活跃的 10 个市场
curl -s "https://gamma-api.polymarket.com/events?active=true&closed=false&limit=10&order=volume&ascending=false" \
  | python3 -c "
import json, sys
for e in json.load(sys.stdin):
    m = e.get('markets', [{}])[0]
    print(e['slug'], '|', m.get('question','')[:60])
"
```

**方法三：验证 slug 是否有数据**

```python
# 验证一个 slug 能否解析并有 CLOB 历史数据
import requests, json, time

slug = "你要验证的-slug"
resp = requests.get(f"https://gamma-api.polymarket.com/events", params={"slug": slug})
data = resp.json()
if not data:
    print("Slug 不存在")
else:
    m = data[0]["markets"][0]
    clob_ids = json.loads(m["clobTokenIds"]) if isinstance(m["clobTokenIds"], str) else m["clobTokenIds"]
    token_id = clob_ids[0]
    end_ts = int(time.time())
    start_ts = end_ts - 7 * 86400
    r = requests.get("https://clob.polymarket.com/prices-history",
                     params={"market": token_id, "startTs": start_ts, "endTs": end_ts, "fidelity": 60})
    history = r.json().get("history", [])
    print(f"最近7天数据点数: {len(history)}")
    if history:
        print(f"最新价格: {history[-1]['p']}")
```

### 添加新市场

1. 在 `TRACKED_MARKETS` 列表中追加 slug 字符串
2. 重建 collector 容器使配置生效：

```bash
cd PolyWatch/data_pipeline
docker compose up -d --build collector
```

collector 下次运行时会自动：
- 将新市场写入 `markets` 表
- 从"最近 30 天"开始拉取历史数据（分批，每批 6 天）

### 其他可配置参数

| 环境变量 | 默认值 | 说明 |
|---------|-------|------|
| `POLL_INTERVAL_SECONDS` | `300` | 每次拉取间隔（秒） |

修改方式：编辑 `data_pipeline/docker-compose.yml` 中 collector 服务的 `environment` 段，然后 `docker compose up -d --build collector`。

---

## 5. 历史数据回溯（backfill）

对于已结束的市场（如 2024 年大选），增量逻辑无法自动获取历史数据，需要手动运行回溯脚本。

### 已完成的回溯

`presidential-election-winner-2024`：2024-01-05 ～ 2024-11-06，共 **7,356 条**记录，已写入数据库。

### 对新市场执行回溯

修改并运行以下脚本（需要激活 venv 或确保 `psycopg2` 已安装）：

```bash
# 激活项目虚拟环境
source /path/to/venv/bin/activate

# 运行回溯脚本
DATABASE_URL=postgresql://polywatch:polywatch@localhost:5433/polywatch \
python3 - <<'EOF'
import sys
sys.path.insert(0, "PolyWatch/data_pipeline/collector")

import os, datetime
os.environ.setdefault("DATABASE_URL", "postgresql://polywatch:polywatch@localhost:5433/polywatch")

from fetcher import resolve_token_id, fetch_price_history
from db import get_connection, upsert_market, insert_price_rows

SLUG       = "你要回溯的-slug"            # ← 修改这里
START_DATE = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)  # ← 修改起始日期
END_DATE   = datetime.datetime(2024, 12, 31, tzinfo=datetime.timezone.utc)  # ← 修改结束日期
CHUNK_DAYS = 6  # 不要超过 6，否则 API 报 400

token_id, question = resolve_token_id(SLUG)
print(f"Resolved: {question}")

conn = get_connection()
upsert_market(conn, token_id, SLUG, question)

cursor = int(START_DATE.timestamp())
end_ts = int(END_DATE.timestamp())
chunk_secs = CHUNK_DAYS * 86400
total_fetched = total_inserted = 0

while cursor < end_ts:
    chunk_end = min(cursor + chunk_secs, end_ts)
    rows = fetch_price_history(token_id, cursor, chunk_end)
    if rows:
        inserted = insert_price_rows(conn, token_id, rows)
        total_fetched += len(rows)
        total_inserted += inserted
        print(f"  {datetime.datetime.fromtimestamp(cursor).date()} "
              f"~ {datetime.datetime.fromtimestamp(chunk_end).date()}: "
              f"fetched {len(rows)}, inserted {inserted}")
    cursor = chunk_end + 1

conn.close()
print(f"\n完成。总计 fetched={total_fetched}, inserted={total_inserted}")
EOF
```

---

## 6. 数据库结构详解

数据库名：`polywatch`，用户名/密码：`polywatch/polywatch`，宿主机端口：`5433`

### 表 1：`markets`（市场元数据）

```sql
CREATE TABLE markets (
    token_id   TEXT PRIMARY KEY,   -- Polymarket CLOB token ID（长数字字符串）
    slug       TEXT NOT NULL,      -- 人类可读的市场标识符
    question   TEXT NOT NULL,      -- 市场问题全文
    active     BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**示例数据：**

```
token_id (前20位)        | slug                                      | question
21742633143463906...     | presidential-election-winner-2024         | Will Donald Trump win the 2024 US Presidential Election?
46553455570564517...     | what-will-happen-before-gta-vi            | Russia-Ukraine Ceasefire before GTA VI?
51616232556781933...     | will-trump-acquire-greenland-before-2027  | Will Trump acquire Greenland before 2027?
```

### 表 2：`price_history`（价格时序数据，核心表）

```sql
CREATE TABLE price_history (
    time       TIMESTAMPTZ  NOT NULL,    -- 价格时间戳（UTC）
    token_id   TEXT         NOT NULL,    -- 关联 markets.token_id
    price      NUMERIC(6,4) NOT NULL,    -- 价格（0.0000 ~ 1.0000，代表概率）
    CONSTRAINT price_history_unique UNIQUE (time, token_id)
);
-- 已创建为 TimescaleDB hypertable，按时间自动分区
```

**价格含义：** 在预测市场中，价格 = 市场对该事件发生的概率估计。
- `0.95` = 市场认为该事件 95% 会发生
- `0.05` = 市场认为该事件 5% 会发生
- 价格剧烈波动 = 潜在的操纵信号

**数据密度：** 每小时约 1 个数据点（fidelity=60 分钟）

### 表 3：`anomaly_events`（异常事件，供算法组使用）

```sql
CREATE TABLE anomaly_events (
    id          SERIAL PRIMARY KEY,
    token_id    TEXT        NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,   -- 异常检测时间
    event_type  TEXT        NOT NULL,   -- 如 'zscore_spike', 'whale_alert'
    severity    TEXT        NOT NULL,   -- 'low', 'medium', 'high'
    detail      JSONB                   -- 算法自定义的详细信息
);
```

**算法组写入示例：**

```python
import psycopg2, json
conn = psycopg2.connect("postgresql://polywatch:polywatch@localhost:5433/polywatch")
with conn.cursor() as cur:
    cur.execute("""
        INSERT INTO anomaly_events (token_id, detected_at, event_type, severity, detail)
        VALUES (%s, NOW(), %s, %s, %s)
    """, (token_id, "zscore_spike", "high", json.dumps({"zscore": 4.2, "price": 0.87})))
conn.commit()
```

---

## 7. 查询数据库——组员操作指南

### 连接方式

**方法一：psql 命令行（推荐）**

```bash
# Docker 内直接访问（不需要本地安装 psql）
docker compose exec timescaledb psql -U polywatch -d polywatch
```

**方法二：宿主机连接（需本地已安装 psql 或 DBeaver 等工具）**

```
Host:     localhost
Port:     5433
Database: polywatch
User:     polywatch
Password: polywatch
```

**方法三：Python 直接连接**

```python
import psycopg2
conn = psycopg2.connect("postgresql://polywatch:polywatch@localhost:5433/polywatch")
```

### 常用查询

#### 查看所有市场

```sql
SELECT slug, question, active, created_at FROM markets;
```

#### 查看每个市场的数据量

```sql
SELECT
    m.slug,
    COUNT(ph.*)         AS 数据点数,
    MIN(ph.time)        AS 最早时间,
    MAX(ph.time)        AS 最新时间,
    ROUND(AVG(ph.price)::numeric, 4) AS 平均价格
FROM price_history ph
JOIN markets m USING (token_id)
GROUP BY m.slug
ORDER BY 数据点数 DESC;
```

#### 获取某个市场的全部价格序列

```sql
SELECT time, price
FROM price_history
JOIN markets USING (token_id)
WHERE slug = 'presidential-election-winner-2024'
ORDER BY time;
```

#### 获取最近 7 天的价格（用于实时分析）

```sql
SELECT time, price
FROM price_history
JOIN markets USING (token_id)
WHERE slug = 'what-will-happen-before-gta-vi'
  AND time >= NOW() - INTERVAL '7 days'
ORDER BY time;
```

#### 查找价格单小时涨跌超过 5% 的时间点（异常检测辅助）

```sql
SELECT
    time,
    price,
    price - LAG(price) OVER (PARTITION BY token_id ORDER BY time) AS price_change
FROM price_history
JOIN markets USING (token_id)
WHERE slug = 'presidential-election-winner-2024'
ORDER BY time
```

```sql
-- 在上面结果基础上筛选大波动
WITH changes AS (
    SELECT
        time, price,
        price - LAG(price) OVER (PARTITION BY token_id ORDER BY time) AS delta
    FROM price_history
    JOIN markets USING (token_id)
    WHERE slug = 'presidential-election-winner-2024'
)
SELECT * FROM changes
WHERE ABS(delta) > 0.05
ORDER BY time;
```

#### 按月统计数据量（验证数据连续性）

```sql
SELECT
    DATE_TRUNC('month', time) AS month,
    COUNT(*) AS points
FROM price_history
JOIN markets USING (token_id)
WHERE slug = 'presidential-election-winner-2024'
GROUP BY month
ORDER BY month;
```

---

## 8. 在 Python 代码中使用数据

### 方法一：用 psycopg2（原生，性能最好）

```python
import psycopg2
import psycopg2.extras

DB_URL = "postgresql://polywatch:polywatch@localhost:5433/polywatch"

def get_price_series(slug: str) -> list[dict]:
    """获取某市场的全部价格序列。"""
    conn = psycopg2.connect(DB_URL)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT ph.time, ph.price
            FROM price_history ph
            JOIN markets m USING (token_id)
            WHERE m.slug = %s
            ORDER BY ph.time
        """, (slug,))
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# 使用示例
data = get_price_series("presidential-election-winner-2024")
print(f"共 {len(data)} 条记录")
print(data[-1])  # 最新一条：{'time': datetime(...), 'price': Decimal('0.9500')}
```

### 方法二：用 pandas（适合算法分析）

```python
import psycopg2
import pandas as pd

DB_URL = "postgresql://polywatch:polywatch@localhost:5433/polywatch"

def get_price_df(slug: str, since: str = None) -> pd.DataFrame:
    """
    返回 DataFrame，列：time(index), price
    since: 可选，如 '2024-10-01'，只获取该日期之后的数据
    """
    conn = psycopg2.connect(DB_URL)
    query = """
        SELECT ph.time, ph.price::float AS price
        FROM price_history ph
        JOIN markets m USING (token_id)
        WHERE m.slug = %(slug)s
        {since_filter}
        ORDER BY ph.time
    """.format(since_filter="AND ph.time >= %(since)s" if since else "")

    df = pd.read_sql(query, conn, params={"slug": slug, "since": since},
                     index_col="time", parse_dates=["time"])
    conn.close()
    return df

# 使用示例（算法组）
df = get_price_df("presidential-election-winner-2024")
print(df.head())
#                            price
# time
# 2024-01-05 00:00:03+00:00  0.5400
# 2024-01-05 01:00:01+00:00  0.5410
# ...

# 计算 Z-Score
df["zscore"] = (df["price"] - df["price"].rolling(24).mean()) / df["price"].rolling(24).std()
spikes = df[df["zscore"].abs() > 3]
print(f"发现 {len(spikes)} 个异常点")
```

### 方法三：用 SQLAlchemy（适合 Flask/FastAPI）

```python
from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine("postgresql://polywatch:polywatch@localhost:5433/polywatch")

with engine.connect() as conn:
    df = pd.read_sql(
        text("SELECT time, price::float FROM price_history "
             "JOIN markets USING (token_id) WHERE slug = :slug ORDER BY time"),
        conn,
        params={"slug": "what-will-happen-before-gta-vi"}
    )
```

---

## 9. 日常运维操作

### 停止/启动服务

```bash
cd PolyWatch/data_pipeline

# 停止（保留数据）
docker compose stop

# 重新启动
docker compose start

# 完全销毁（数据卷也删除，慎用！）
docker compose down -v
```

### 查看日志

```bash
# 实时跟踪 collector 日志
docker compose logs -f collector

# 查看最近 100 行
docker compose logs collector --tail=100

# 查看 timescaledb 日志
docker compose logs timescaledb
```

### 强制触发一次数据拉取

collector 每 5 分钟自动拉取一次。如需立即拉取：

```bash
# 重启 collector（会立即执行一次 collect_once()）
docker compose restart collector
```

### 数据库备份

```bash
# 导出完整数据库为 SQL 文件
docker compose exec timescaledb pg_dump -U polywatch polywatch > backup_$(date +%Y%m%d).sql

# 恢复
docker compose exec -T timescaledb psql -U polywatch polywatch < backup_20260306.sql
```

### 导出数据为 CSV（供离线分析）

```bash
# 在 psql 内执行
docker compose exec timescaledb psql -U polywatch -d polywatch -c "\COPY (
  SELECT m.slug, ph.time, ph.price
  FROM price_history ph JOIN markets m USING (token_id)
  ORDER BY m.slug, ph.time
) TO '/tmp/price_history.csv' CSV HEADER"

# 将 CSV 从容器复制到宿主机
docker cp data_pipeline-timescaledb-1:/tmp/price_history.csv ./price_history.csv
```

---

## 10. 运行自动化测试

数据管道共有 **13 个自动化测试**：6 个单元测试（无需网络）+ 7 个集成测试（需要 DB）。

### 运行所有测试

```bash
# 确保 TimescaleDB 容器正在运行
cd PolyWatch/data_pipeline && docker compose up -d timescaledb

# 在 repo 根目录运行
cd PolyWatch
DATABASE_URL=postgresql://polywatch:polywatch@localhost:5433/polywatch \
pytest tests/ -v
```

### 预期输出

```
tests/data_pipeline/test_fetcher.py::TestResolveTokenId::test_returns_token_id_and_question_on_success PASSED
tests/data_pipeline/test_fetcher.py::TestResolveTokenId::test_returns_none_on_empty_response PASSED
tests/data_pipeline/test_fetcher.py::TestResolveTokenId::test_handles_network_error_gracefully PASSED
tests/data_pipeline/test_fetcher.py::TestFetchPriceHistory::test_returns_list_of_dicts_with_time_and_price PASSED
tests/data_pipeline/test_fetcher.py::TestFetchPriceHistory::test_returns_empty_list_on_empty_history PASSED
tests/data_pipeline/test_fetcher.py::TestFetchPriceHistory::test_returns_empty_list_on_error PASSED
tests/data_pipeline/test_db.py::TestUpsertMarket::test_inserts_new_market PASSED
tests/data_pipeline/test_db.py::TestUpsertMarket::test_is_idempotent_on_duplicate PASSED
tests/data_pipeline/test_db.py::TestInsertPriceRows::test_inserts_rows_and_returns_count PASSED
tests/data_pipeline/test_db.py::TestInsertPriceRows::test_skips_duplicates_silently PASSED
tests/data_pipeline/test_db.py::TestInsertPriceRows::test_returns_zero_for_empty_rows PASSED
tests/data_pipeline/test_db.py::TestGetLatestTimestamp::test_returns_none_when_no_data PASSED
tests/data_pipeline/test_db.py::TestGetLatestTimestamp::test_returns_most_recent_time PASSED

13 passed in X.XXs
```

---

## 11. 常见问题排查

### Q: `docker compose ps` 显示 timescaledb 不是 healthy

```bash
# 查看数据库启动日志
docker compose logs timescaledb

# 常见原因：init.sql 语法错误，或端口 5433 被占用
# 检查端口
ss -tlnp | grep 5433
```

### Q: collector 日志显示 `DB connection failed`

确认 timescaledb 容器正常运行，且 healthy 状态。collector 依赖 timescaledb 健康检查通过后才启动。

### Q: collector 日志显示 `400 Bad Request ... interval is too long`

CLOB API 单次请求不能超过约 7 天。检查 `main.py` 中 `FETCH_CHUNK_DAYS` 是否 ≤ 6。

### Q: collector 日志显示 `Could not resolve slug`

该 slug 对应的市场已从 Polymarket 下线或改名。前往 [polymarket.com](https://polymarket.com) 确认市场是否仍然存在，更新 `TRACKED_MARKETS` 列表。

### Q: 从宿主机连不上数据库（非 Docker 内）

确认使用端口 `5433`（非默认的 5432）：

```bash
psql -h localhost -p 5433 -U polywatch -d polywatch
```

### Q: `psycopg2` 安装失败

```bash
# 安装二进制版本（不需要编译）
pip install psycopg2-binary
```

### Q: 数据库有数据但 price_history 是空的

可能是首次启动时市场列表中有无效 slug 导致没有数据写入。检查 collector 日志确认 `inserted N new rows`。如果是已结束的历史市场，需要运行[回溯脚本](#5-历史数据回溯backfill)。

---

## 12. 当前数据库状态（快照）

> 截至 2026-03-06

| 市场 slug | 用途 | 行数 | 时间范围 | 均价 |
|-----------|------|------|---------|------|
| `presidential-election-winner-2024` | 算法回测（已结束）| 7,356 | 2024-01-05 ~ 2024-11-06 | 0.527 |
| `what-will-happen-before-gta-vi` | 实时监控（俄乌停火）| ~720 | 2026-02-04 ~ 持续更新 | 0.585 |
| `will-trump-acquire-greenland-before-2027` | 实时监控（特朗普政策）| ~710 | 2026-02-04 ~ 持续更新 | 0.115 |

> **注意：** 数据库中另有3个旧市场的元数据（fed-decision、2028大选、民主党提名人），这些市场没有价格数据，不影响使用。

---

## 附录：文件结构

```
data_pipeline/
├── docker-compose.yml          # 服务编排：timescaledb + collector
├── db/
│   └── init.sql                # 数据库 schema（首次启动自动执行）
├── collector/
│   ├── Dockerfile              # collector 镜像定义
│   ├── requirements.txt        # Python 依赖：requests, psycopg2-binary, schedule
│   ├── fetcher.py              # API 请求层：resolve_token_id, fetch_price_history
│   ├── db.py                   # 数据库操作层：upsert_market, insert_price_rows, get_latest_timestamp
│   └── main.py                 # 主入口：TRACKED_MARKETS 配置 + 调度循环
└── README.md                   # 英文快速参考

tests/data_pipeline/
├── test_fetcher.py             # 6 个单元测试（mock HTTP）
└── test_db.py                  # 7 个集成测试（真实 DB）
```
