# PolyWatch 前端项目概述（中文版）

---

## 一、项目背景

- **里程碑 1（已完成）：** 使用 Streamlit 搭建的原型，展示市场列表、价格图表与异常事件。
- **里程碑 2（当前）：** 使用现代 Web 技术栈重构前端，仍使用模拟数据，但已为后续 API 接入预留接口。
- **后端现状：** 数据管道已存在（TimescaleDB + Python 采集器），但尚无 HTTP API 层，后端数据格式未最终确定。
- **算法团队：** 异常检测算法正在开发中，前端通过服务层与其解耦。

---

## 二、技术栈

| 类别 | 技术 | 版本 |
|:---|:---|:---|
| 框架 | Next.js（App Router） | 16.1.6 |
| 语言 | TypeScript | ^5 |
| 样式 | Tailwind CSS v4 | ^4（通过 CSS 变量配置主题，无 `tailwind.config.ts`） |
| UI 组件库 | shadcn/ui | — |
| 图表 | Apache ECharts + echarts-for-react | v6 |
| 数据请求 | TanStack Query | ^5（已安装，尚未启用） |
| 图标 | lucide-react | ^0.577 |
| 包管理器 | pnpm | 10.30.3 |
| Node.js | — | v24.14.0 |

> **ECharts 选型原因：** 支持 7000+ 数据点高性能渲染，原生支持 `markPoint`/`dataZoom`，适合时序异常标注。K 线图已被排除，因为预测市场数据是每小时单点价格，无 OHLC 结构。

---

## 三、核心架构原则：服务层隔离

```
lib/mock/data.ts       ← 模拟数据（当前阶段）
lib/services/index.ts  ← 数据入口（唯一需要改动的文件）
components/            ← UI 组件（不感知数据来源）
```

- **所有组件只从 `lib/services/index.ts` 获取数据**，从不直接引用模拟数据文件。
- 未来接入 FastAPI 时，**只需修改 `services/index.ts`**，将 mock 导入替换为 `fetch()` 调用，组件代码无需改动。

---

## 四、文件结构

```
polywatch-frontend/
├── app/
│   ├── layout.tsx          # 根布局（ThemeProvider、suppressHydrationWarning）
│   ├── page.tsx            # 单页面仪表盘：侧边栏状态 + 右侧面板组装
│   └── globals.css         # Tailwind v4 主题 CSS 变量（亮色 + 暗色）
├── components/
│   ├── MarketSidebar.tsx   # 左侧：全高度可折叠市场列表
│   ├── PriceChart.tsx      # 中部：ECharts 折线图 + 异常标注（主题感知）
│   ├── AnomalyFeed.tsx     # 图表下方：异常事件列表
│   ├── StatsBar.tsx        # 当前市场统计数据（4 张卡片）
│   ├── ThemeToggle.tsx     # 亮/暗模式切换按钮
│   └── ui/                 # shadcn 组件（badge、button、card、scroll-area、separator）
├── lib/
│   ├── mock/
│   │   └── data.ts         # 模拟数据（3 个市场、价格序列、7 条异常事件）
│   ├── services/
│   │   └── index.ts        # 服务层：getMarkets / getPriceHistory / getAnomalyEvents / getMarketStats
│   ├── theme.tsx           # ThemeProvider 上下文 + useTheme hook
│   └── utils.ts            # shadcn cn() 工具函数
├── package.json
└── tsconfig.json
```

---

## 五、页面布局

单页面仪表盘，默认暗色金融终端风格（参考 Bloomberg/TradingView）。

```
┌─────────────┬─────────────────────────────────────────────┐
│             │  顶栏：PolyWatch 标题 + 主题切换按钮           │
│  市场侧边栏  ├─────────────────────────────────────────────┤
│  （全高度，  │  市场标题 + slug + 状态（ENDED 标签）          │
│  可折叠）    ├─────────────────────────────────────────────┤
│             │  StatsBar：当前价格 / 数据点数 / 最大波动 / 异常数│
│  展开：w-56  ├─────────────────────────────────────────────┤
│  折叠：w-14  │  PriceChart（420px，折线图 + dataZoom + 异常标注）│
│             ├─────────────────────────────────────────────┤
│  << 折叠    │  AnomalyFeed（280px，可滚动异常事件列表）       │
│             ├─────────────────────────────────────────────┤
│             │  底栏：项目信息                               │
└─────────────┴─────────────────────────────────────────────┘
```

---

## 六、各组件说明

### MarketSidebar（市场侧边栏）
- 展示所有监控市场，点击切换右侧所有组件数据
- 折叠状态（`w-14`）：仅显示彩色圆点；展开状态（`w-56`）：显示完整名称、价格、涨跌
- 当前选中市场高亮（`bg-accent`）

### StatsBar（统计栏）
- 接受 `slug` prop，调用 `getMarketStats(slug)` 获取数据
- 4 张居中卡片：**当前价格**（含 24h 涨跌）/ **数据点数** / **最大单步波动** / **检测到的异常数**

### PriceChart（价格图表）
- ECharts 折线图，通过 `echarts-for-react` 渲染（动态导入，关闭 SSR）
- X 轴：时间；Y 轴：概率（0–1，显示为百分比）
- `dataZoom`（滑块 + 内部拖拽）支持平移/缩放
- 异常事件以彩色圆点 `markPoint` 标注：红=高、黄=中、蓝=低
- **主题感知**：通过 `useTheme()` hook 自动切换亮/暗配色

### AnomalyFeed（异常事件流）
- 反向时间顺序列表，按市场过滤
- 彩色严重程度徽章（红/黄/蓝）+ 事件类型图标

### ThemeToggle（主题切换）
- 太阳/月亮图标，点击切换亮暗模式
- 持久化至 `localStorage`（key：`polywatch-theme`），默认暗色

---

## 七、模拟数据说明

当前共 **3 个市场**、**7 条异常事件**：

| 市场 slug | 描述 | 状态 |
|:---|:---|:---|
| `presidential-election-winner-2024` | 2024 美国大选 Trump 是否获胜 | 已结束（ENDED） |
| `what-will-happen-before-gta-vi` | 俄乌停火能否在 GTA6 发布前实现 | 进行中 |
| `will-trump-acquire-greenland-before-2027` | Trump 能否在 2027 年前收购格陵兰 | 进行中 |

价格序列由确定性随机游走算法生成（可复现），每小时或每 37 小时一个数据点。

---

## 八、后端接入路径

后端团队提供 FastAPI 接口后，前端接入步骤：

1. 在 `lib/services/index.ts` 中将 mock 导入替换为 `fetch()` 调用
2. 若字段名与前端类型不符，在同一文件中添加数据转换映射
3. 所有组件代码**无需改动**
4. 可选：启用 TanStack Query（`useQuery` 包装服务函数），获得缓存、自动刷新、错误处理能力
5. 可选：添加 Zod 运行时数据校验

**预计从模拟数据切换到真实 API 的工作量：修改 1 个文件（`lib/services/index.ts`）。**

---

## 九、本地开发运行

```bash
# 进入前端目录
cd polywatch-frontend

# 安装依赖（首次）
pnpm install

# 启动开发服务器
pnpm dev
```

访问 `http://localhost:3000` 即可查看仪表盘。
