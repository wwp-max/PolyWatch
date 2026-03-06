# PolyWatch

**PolyWatch** 是一个面向 Polymarket 预测市场的市场完整性监测系统，用于检测价格操纵（Pump & Dump）、异常波动及可疑交易行为。

> Course: CS6290 Privacy-Enhancing Technologies | Group 16 | CityU Hong Kong

---

## 项目目标

通过对 Polymarket 实时价格数据进行采集、存储与分析，识别潜在的市场操纵信号，为去中心化预测市场生态提供透明度与安全洞察。

---

## 目录结构

```
PolyWatch/
├── data_pipeline/          # M2：数据采集管道（TimescaleDB + Docker）
│   ├── collector/          #   自动采集器（Python）
│   │   ├── main.py         #   调度主入口，TRACKED_MARKETS 配置
│   │   ├── fetcher.py      #   Polymarket API 请求层
│   │   └── db.py           #   数据库写入层（幂等）
│   ├── db/
│   │   ├── init.sql        #   数据库 schema
│   │   └── price_history_seed.csv  # 历史种子数据（10,564 条）
│   ├── docker-compose.yml  #   服务编排
│   └── README.md           #   数据管道完整操作手册（中文）
├── core_analysis/          # M3+：异常检测算法（Z-Score、Whale Alert 等）
├── data_ingestion/         # 早期数据摄取模块（已被 data_pipeline 取代）
├── forensics/              # 取证分析模块
├── docs/                   # 项目文档
│   └── data-pipeline-guide.md  # 数据管道手册（同 data_pipeline/README.md）
├── tests/
│   └── data_pipeline/      # 自动化测试（13个：6单元 + 7集成）
├── requirements.txt
└── README.md               # 本文件
```

---

## 快速开始

### 前置条件

- Docker Desktop（含 WSL2 集成）已安装并运行
- Python 3.10+

### 启动数据管道

```bash
cd data_pipeline
docker compose up -d
docker compose logs -f collector
```

**首次启动需导入历史种子数据**，详见 [`data_pipeline/README.md`](data_pipeline/README.md) 第 3 节。

### 连接数据库

```
postgresql://polywatch:polywatch@localhost:5433/polywatch
```

### 运行测试

```bash
DATABASE_URL=postgresql://polywatch:polywatch@localhost:5433/polywatch \
pytest tests/ -v
```

---

## 当前数据

| 市场 | 用途 | 数据量 |
|------|------|--------|
| `presidential-election-winner-2024` | 算法回测（已结束）| 7,356 条（2024-01-05 ~ 2024-11-06）|
| `what-will-happen-before-gta-vi` | 实时监控（俄乌停火）| ~720 条，持续更新 |
| `will-trump-acquire-greenland-before-2027` | 实时监控（特朗普政策）| ~710 条，持续更新 |

---

## 模块说明

### data_pipeline（M2，已完成）

自动化数据采集管道，每 5 分钟从 Polymarket CLOB API 拉取价格数据，写入 TimescaleDB。
详见 [data_pipeline/README.md](data_pipeline/README.md)。

### core_analysis（M3+，进行中）

异常检测算法模块，包含：
- Z-Score 价格异常检测
- Whale Alert（大额交易预警）

算法组可通过 `anomaly_events` 表将检测结果写回数据库，供可视化模块读取。

### forensics（进行中）

取证分析模块，用于对历史异常事件进行深入调查和证据归档。

---

## 团队

| 姓名 | SID | 负责模块 |
|------|-----|---------|
| LIN Tao | 59843612 | data_pipeline（M2 负责人）|

Course: **CS6290 Privacy-Enhancing Technologies**, CityU Hong Kong
