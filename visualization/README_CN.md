# PolyWatch — Polymarket 异常监控仪表盘

PolyWatch 是一个用于监测 [Polymarket](https://polymarket.com/) 预测市场价格异常的全栈应用。本仓库是**前端部分**，提供一个交互式仪表盘，实时展示市场价格走势和异常事件。

> **课程项目**：CityU Hong Kong — CS6290

---

## 这个项目是做什么的？

Polymarket 是一个去中心化预测市场平台，用户可以对真实事件（如选举结果、政策变化等）进行押注交易。每个市场的价格反映了人们对事件发生概率的判断——价格 0.65 意味着市场认为该事件有 65% 的概率发生。

**PolyWatch** 的目标是**自动检测这些市场中的异常价格行为**，比如：

| 异常类型 | 含义 |
|----------|------|
| **Z-Score Spike** | 价格突然大幅偏离历史均值（统计学方法检测） |
| **Whale Trade** | 大额交易（"巨鲸"交易）导致价格剧烈波动 |
| **Whale Directional Bias** | 大额交易集中在同一方向，可能存在操纵 |
| **Benford Violation** | 价格变动的数字分布不符合本福特定律，暗示可能有人为操纵 |

前端仪表盘让你可以：
- 在左侧栏切换不同的预测市场
- 查看每个市场的价格历史走势图（支持缩放和拖拽）
- 查看统计信息（平均价格、数据点数量、数据时间范围）
- 浏览检测到的异常事件列表（包含严重程度和详细参数）

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 框架 | [Next.js 16](https://nextjs.org/) (App Router) |
| UI 库 | [React 19](https://react.dev/) |
| 语言 | [TypeScript 5](https://www.typescriptlang.org/) |
| 样式 | [Tailwind CSS 4](https://tailwindcss.com/) + [shadcn/ui](https://ui.shadcn.com/) |
| 图表 | [Apache ECharts 6](https://echarts.apache.org/) (via echarts-for-react) |
| 数据请求 | [TanStack React Query 5](https://tanstack.com/query) |
| 图标 | [Lucide React](https://lucide.dev/) |
| 包管理器 | [pnpm](https://pnpm.io/) |
| 后端 | [Flask](https://flask.palletsprojects.com/) (Python) |
| 数据库 | [TimescaleDB](https://www.timescale.com/) (PostgreSQL 扩展，适合时序数据) |
| 容器化 | [Docker Compose](https://docs.docker.com/compose/) (数据库 + 数据采集器) |

---

## 项目结构

```
polywatch-frontend/
├── app/                        # Next.js App Router 页面
│   ├── layout.tsx              #   根布局（全局 Provider、字体、元数据）
│   ├── page.tsx                #   主页面（仪表盘布局）
│   └── globals.css             #   全局样式 + Tailwind 主题变量
│
├── components/                 # React 组件
│   ├── MarketSidebar.tsx       #   左侧市场列表（可折叠）
│   ├── StatsBar.tsx            #   统计卡片栏（均价、数据量、时间范围）
│   ├── PriceChart.tsx          #   价格走势图（ECharts，含异常标记点）
│   ├── AnomalyFeed.tsx         #   异常事件列表（滚动、分类、详情）
│   ├── ThemeToggle.tsx         #   深色/浅色主题切换按钮
│   └── ui/                     #   shadcn/ui 基础组件（Badge, Card 等）
│
├── lib/                        # 核心逻辑库
│   ├── types.ts                #   TypeScript 类型定义（与后端 API 对齐）
│   ├── api.ts                  #   纯 fetch 函数（封装后端 API 调用）
│   ├── hooks/index.ts          #   React Query hooks（组件的唯一数据源）
│   ├── providers.tsx           #   QueryClientProvider 包装器
│   ├── theme.tsx               #   主题 Context（深色/浅色模式）
│   └── utils.ts                #   工具函数（cn 合并 class 名）
│
├── backend/                    # 后端代码（Python Flask + 数据分析）
│   ├── core_analysis/          #   异常检测算法 + API 服务器
│   │   ├── api_server.py       #     Flask REST API（前端调用入口）
│   │   ├── db_interface.py     #     数据库查询接口
│   │   ├── zscore_detector.py  #     Z-Score 异常检测
│   │   ├── benford_detector.py #     本福特定律检测
│   │   └── whale_alert.py      #     巨鲸交易检测
│   ├── data_pipeline/          #   数据采集流水线
│   │   ├── docker-compose.yml  #     Docker Compose（TimescaleDB + 采集器）
│   │   ├── db/init.sql         #     数据库初始化脚本
│   │   └── collector/          #     价格数据采集器（定时从 Polymarket 拉数据）
│   └── requirements.txt        #   Python 依赖
│
├── .env.local                  # 环境变量（后端 API 地址，不提交到 git）
├── package.json                # Node.js 依赖和脚本
└── pnpm-lock.yaml              # 锁定的依赖版本
```

---

## 数据流

整个应用的数据流如下：

```
Polymarket API ──▸ 数据采集器 ──▸ TimescaleDB ──▸ Flask API ──▸ 前端
(公开行情)        (Docker 容器)    (Docker 容器)    (Python)      (Next.js)
                  每 5 分钟拉取     时序数据存储      :5001         :3000
```

前端内部的数据流：

```
Flask API (:5001)
    │
    ▼
lib/api.ts          ← 纯 fetch 函数，不依赖 React
    │
    ▼
lib/hooks/index.ts  ← React Query hooks，自动缓存/重试/加载状态
    │
    ▼
组件 (page.tsx, MarketSidebar, PriceChart, StatsBar, AnomalyFeed)
```

---

## 手把手运行指南

### 前置条件

请确保你的电脑上已经安装了以下软件：

| 软件 | 最低版本 | 检查命令 | 安装方式 |
|------|---------|---------|---------|
| **Node.js** | 18+ | `node -v` | [nodejs.org](https://nodejs.org/) 或 `brew install node` |
| **pnpm** | 8+ | `pnpm -v` | `npm install -g pnpm` |
| **Python** | 3.9+ | `python3 --version` | [python.org](https://python.org/) 或 `brew install python` |
| **Docker** | 20+ | `docker --version` | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **Docker Compose** | 2+ | `docker compose version` | 随 Docker Desktop 一起安装 |

> **提示**：macOS 用户推荐用 [Homebrew](https://brew.sh/) 安装以上工具。

---

### 第一步：启动数据库（TimescaleDB）

数据库通过 Docker Compose 运行，已预配置好初始化脚本。

```bash
# 进入数据管道目录
cd backend/data_pipeline

# 启动 TimescaleDB（后台运行）
docker compose up -d timescaledb

# 等待数据库就绪（看到 "healthy" 状态即可）
docker compose ps
```

你应该看到类似输出：
```
NAME                    STATUS              PORTS
data_pipeline-timescaledb-1   Up (healthy)   0.0.0.0:5433->5432/tcp
```

**数据库连接信息**（你通常不需要手动连接，但以防万一）：
- 主机：`localhost`
- 端口：`5433`
- 数据库名：`polywatch`
- 用户名：`polywatch`
- 密码：`polywatch`

---

### 第二步：导入数据（如果数据库是空的）

如果你的数据库是全新的，需要导入种子数据。`init.sql` 会自动创建表结构，但价格历史数据需要手动导入：

```bash
# 仍然在 backend/data_pipeline 目录下
# 导入种子数据（CSV）
docker compose exec timescaledb psql -U polywatch -d polywatch \
  -c "\COPY price_history(time, token_id, price) FROM '/docker-entrypoint-initdb.d/../price_history_seed.csv' CSV HEADER"
```

或者，启动数据采集器自动从 Polymarket 拉取最新数据：

```bash
# 启动采集器（会自动每 5 分钟拉取一次）
docker compose up -d collector
```

---

### 第三步：启动后端 API 服务

```bash
# 回到项目根目录
cd ../..

# 创建 Python 虚拟环境（只需第一次）
cd backend
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate    # macOS / Linux
# venv\Scripts\activate     # Windows

# 安装 Python 依赖（只需第一次）
pip install -r requirements.txt

# 启动 API 服务器
python -m core_analysis.api_server
```

你应该看到：
```
==================================================
  PolyWatch API Server
  http://localhost:5001
==================================================

可用接口：
  GET  /api/health                - 健康检查
  GET  /api/markets               - 市场列表
  GET  /api/markets/<slug>/prices  - 价格历史
  GET  /api/markets/<slug>/stats   - 市场统计
  GET  /api/markets/<slug>/gaps    - 数据缺口
  GET  /api/anomalies              - 异常事件列表
  POST /api/analyze/<slug>         - 实时分析
```

**验证后端是否正常**（新开一个终端窗口）：

```bash
# 测试健康检查
curl http://127.0.0.1:5001/api/health
# 应该返回: {"service":"polywatch-api","status":"ok"}

# 测试市场列表
curl http://127.0.0.1:5001/api/markets
# 应该返回一个 JSON 数组，包含多个市场
```

---

### 第四步：启动前端

```bash
# 回到项目根目录（polywatch-frontend/）
cd ..

# 安装前端依赖（只需第一次）
pnpm install

# 确认环境变量文件存在
cat .env.local
# 应该显示: NEXT_PUBLIC_API_URL=http://127.0.0.1:5001
# 如果文件不存在，手动创建：
# echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:5001" > .env.local

# 启动开发服务器
pnpm dev
```

然后在浏览器中打开 **http://localhost:3000**，你就能看到仪表盘了！

---

### 快速启动速查表

如果你已经完成过初始设置，日常启动只需要：

```bash
# 终端 1：数据库
cd backend/data_pipeline && docker compose up -d timescaledb

# 终端 2：后端 API
cd backend && source venv/bin/activate && python -m core_analysis.api_server

# 终端 3：前端
pnpm dev
```

然后打开浏览器访问 http://localhost:3000。

---

## 后端 API 接口文档

前端调用的 API 一览：

### `GET /api/markets`

返回所有市场列表。

```json
[
  {
    "slug": "presidential-election-winner-2024",
    "question": "Will Donald Trump win the 2024 US Presidential Election?",
    "active": true,
    "lastPrice": 0.95,
    "prevPrice": 0.93
  }
]
```

### `GET /api/markets/<slug>/prices`

返回指定市场的价格历史（按时间排序）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `since` | query (可选) | ISO 日期字符串，只返回该日期之后的数据 |

```json
[
  { "time": "2024-10-01T00:00:00+00:00", "price": 0.52 },
  { "time": "2024-10-01T01:00:00+00:00", "price": 0.53 }
]
```

### `GET /api/markets/<slug>/stats`

返回指定市场的统计信息。

```json
{
  "slug": "presidential-election-winner-2024",
  "question": "Will Donald Trump win...",
  "rowCount": 4320,
  "firstTime": "2024-10-01T00:00:00+00:00",
  "lastTime": "2024-11-06T12:00:00+00:00",
  "avgPrice": 0.5834
}
```

### `GET /api/anomalies`

返回异常事件列表。

| 参数 | 类型 | 说明 |
|------|------|------|
| `slug` | query (可选) | 按市场 slug 筛选 |
| `severity` | query (可选) | 按严重程度筛选：`low` / `medium` / `high` |

```json
[
  {
    "id": 1,
    "marketSlug": "presidential-election-winner-2024",
    "detectedAt": "2024-10-15T08:00:00+00:00",
    "eventType": "zscore_spike",
    "severity": "high",
    "detail": { "z_score": 3.2, "threshold": 2.5, "price": 0.68 }
  }
]
```

### `POST /api/analyze/<slug>`

对指定市场运行实时异常检测（不写入数据库，仅返回分析结果）。

---

## 常见问题

### 前端页面显示 "Failed to load markets"

**原因**：前端无法连接到后端 API。

检查清单：
1. 后端 API 是否在运行？终端里看看有没有 Flask 输出。
2. 端口是否正确？确认 `.env.local` 里写的是 `http://127.0.0.1:5001`。
3. 用 `curl http://127.0.0.1:5001/api/health` 测试后端是否响应。

### 后端报数据库连接错误

**原因**：TimescaleDB 没有启动或者端口不对。

```bash
# 检查 Docker 容器状态
cd backend/data_pipeline && docker compose ps

# 如果容器没跑起来
docker compose up -d timescaledb

# 等它变成 healthy 状态
docker compose ps
```

### 图表显示 "No price data available"

**原因**：数据库里没有对应市场的价格数据。

确认数据是否已导入：
```bash
# 连接数据库查看
docker compose exec timescaledb psql -U polywatch -d polywatch \
  -c "SELECT slug, COUNT(*) FROM price_history JOIN markets USING (token_id) GROUP BY slug;"
```

### pnpm install 报错

尝试清除缓存重装：
```bash
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

---

## 开发指南

### 构建生产版本

```bash
pnpm build    # 编译 + 类型检查 + 优化
pnpm start    # 启动生产服务器
```

### 类型检查

```bash
npx tsc --noEmit
```

### 代码检查

```bash
pnpm lint
```

### 修改后端 API 地址

编辑项目根目录的 `.env.local` 文件：

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:5001
```

修改后需要重启前端开发服务器（`pnpm dev`）。

---

## 许可证

本项目为 CityU CS6290 课程项目，仅供学术用途。
