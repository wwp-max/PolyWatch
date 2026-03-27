# Findings & Decisions — 成员 C 核心算法工程师

## 需求分析

### 项目背景
- PolyWatch：Polymarket 预测市场完整性监测系统
- 成员 B 已搭好数据管道 + TimescaleDB + 共享接口
- 成员 C 负责：把数据变成结论（异常检测算法引擎）

### 核心交付物
1. **算法 1：Z-Score / 移动平均线策略** — 检测突发价格操纵
2. **算法 2：Benford's Law 检验** — 检测人为伪造的交易量
3. **算法 3：鲸鱼警报 (Whale Alert)** — 大单监测
4. **回测系统** — 用 2024 美国大选历史数据验证算法准确率
5. **准确率验证报告** — False Positive / False Negative 分析
6. **Jupyter Notebooks + Python Scripts**

---

## 现有代码分析（成员 B 已提供）

### 可直接使用的接口（core_analysis/db_interface.py）
- `get_price_series(slug, since=None)` → 返回 DataFrame(index=time, columns=[price])
- `get_token_id_by_slug(slug)` → 返回 token_id
- `write_anomaly(token_id, detected_at, event_type, severity, detail)` → 写入异常事件
- `query_anomalies(slug, severity)` → 查询异常
- `get_active_slugs()` → 获取有数据的市场列表
- `get_market_stats()` → 市场统计信息

### 已有的骨架代码
- `core_analysis/zscore_detector.py` — 基础 ZScoreDetector 类（window=30, threshold=2.5），仅做 rolling z-score
- `core_analysis/whale_alert.py` — 基础 WhaleAlert 类（size_threshold=200），仅做简单筛选

### 可用数据
| 市场 | 数据量 | 时间范围 | 用途 |
|------|--------|---------|------|
| presidential-election-winner-2024 | 7,356 条 | 2024-01-05 ~ 2024-11-06 | 回测 |
| what-will-happen-before-gta-vi | ~780+ 条 | 2026-02-04 ~ 持续 | 实时监控 |
| will-trump-acquire-greenland-before-2027 | ~770+ 条 | 2026-02-04 ~ 持续 | 实时监控 |

### 数据库表结构
- `price_history`：(time, token_id, price)，price 范围 0~1 代表概率
- `anomaly_events`：(id, token_id, detected_at, event_type, severity, detail)

### 数据局限性（重要！）
- **当前只有价格数据，没有交易量（volume）和单笔交易（individual trades）数据**
- Benford's Law 需要交易量数据 → 需要从 Polymarket CLOB API 额外获取
- Whale Alert 需要单笔交易数据 → 需要从 API 额外获取或用 The Graph subgraph
- 这是成员 B 数据管道目前未覆盖的部分，需要自行补充数据获取逻辑

---

## 算法设计头脑风暴

### 算法 1：Z-Score / 移动平均线策略

**目标：** 检测价格突然异常波动（可能的价格操纵）

**设计思路：**
1. **基础 Z-Score 检测器**（已有骨架）
   - 滚动窗口计算 mean 和 std
   - Z-Score = (price - rolling_mean) / rolling_std
   - |Z-Score| > threshold → 标记为异常
   
2. **增强策略（需要新增）**：
   - **多窗口检测**：短期(6h)、中期(24h)、长期(72h) 三个窗口，任一触发即报警
   - **EWMA（指数加权移动平均）**：对近期数据赋更高权重，更灵敏
   - **价格变化率检测**：不仅看绝对价格，也看相邻时间点的价格变化幅度
   - **异常持续时间判断**：单点异常 vs 连续异常（连续异常更可能是真事件而非操纵）
   - **动态阈值**：根据市场波动性自动调整阈值（高波动市场用更高阈值）

3. **可调参数**：
   - `window_sizes`: [6, 24, 72]
   - `z_threshold`: 2.5 (default), 可调
   - `min_std`: 0.001（防止低波动时 std≈0 导致 z-score 爆炸）

### 算法 2：Benford's Law 检验

**目标：** 检测人为伪造的交易量

**原理：** 自然产生的数字，其首位数字分布符合 Benford's Law（1 出现概率 ~30.1%，2 出现概率 ~17.6%，...9 出现概率 ~4.6%）。如果交易量的首位数字分布偏离 Benford 分布，说明数据可能被人为伪造。

**设计思路：**
1. 从 CLOB API 获取交易量/交易数据
2. 提取每笔交易金额的首位数字
3. 统计首位数字分布
4. 用卡方检验（chi-squared test）计算与 Benford 理论分布的偏离程度
5. p-value < 0.05 → 拒绝"自然分布"假设 → 标记为可疑

**数据问题：**
- 当前数据管道只有 price 没有 volume
- 方案 A：直接用 price 的变化幅度(delta)做 Benford 检验（可行但不完全对口）
- 方案 B：从 Polymarket CLOB API 的 `/trades` 端点拉取交易数据（更准确）
- 方案 C：用 The Graph subgraph 获取链上交易数据
- **建议：先用方案 A 做 MVP，同时尝试方案 B 获取真实交易量**

### 算法 3：鲸鱼警报 (Whale Alert)

**目标：** 监测大额交易，单笔或短时间内累计金额超阈值即报警

**设计思路：**
1. **单笔大额检测**：单笔交易金额 > threshold → 报警
2. **累计大额检测**：某地址在短时间窗口(如 1h)内累计交易额 > threshold → 报警
3. **价格影响分析**：大额交易前后价格变化幅度（是否导致异常波动）
4. **方向偏向检测**：某地址连续单向买入/卖出 → 更可疑

**数据问题（同上）：** 需要单笔交易数据，当前数据管道未覆盖

### 回测系统

**目标：** 用 2024 年大选数据验证算法准确率

**设计思路：**
1. **已知事件标注**：手动标注 2024 大选期间的已知重大事件（辩论、枪击事件、退选等）
2. **区分"正常波动"和"异常操纵"**：
   - 真实事件导致的价格波动 = True Positive（算法应该检测到，但不是操纵）
   - 无明显事件时的异常 = 可能的操纵信号
3. **评估指标**：
   - 灵敏度(Sensitivity)：是否能检测到已知异常
   - 特异度(Specificity)：是否把正常波动误判为异常
   - False Positive Rate / False Negative Rate
4. **参数调优**：网格搜索不同 window 和 threshold 组合，找到最优参数

---

## 技术决策

| 决策 | 理由 |
|------|------|
| 先聚焦 Z-Score 算法（有现成数据） | 价格数据已齐全，可以立即开始 |
| Benford 先用价格变化量做 MVP | 交易量数据暂缺，先出原型，后续补数据 |
| Whale Alert 需等交易数据 | 必须有单笔交易数据才有意义 |
| 回测用 2024 大选数据 | 7,356 条数据，时间跨度近 1 年，事件丰富 |
| 输出为 Jupyter Notebook + Python 模块 | 符合交付要求，Notebook 方便展示 |
| 检测结果统一写入 anomaly_events 表 | 复用成员 B 的接口，前端可直接读取 |

---

## 2024 年大选重大事件时间线（用于回测标注）

| 日期 | 事件 | 预期价格影响 |
|------|------|-------------|
| 2024-01-15 | Iowa Caucus | Trump 大幅领先，价格上涨 |
| 2024-03-05 | Super Tuesday | Trump 横扫，价格上涨 |
| 2024-06-27 | 首场辩论 Biden vs Trump | Biden 表现差，Trump 价格飙升 |
| 2024-07-13 | Trump 枪击事件 | 价格剧烈波动 |
| 2024-07-21 | Biden 退选 | 价格大幅波动 |
| 2024-08-22 | DNC 民主党大会 | Harris 势头，Trump 价格下降 |
| 2024-09-10 | Harris vs Trump 辩论 | 价格波动 |
| 2024-10-01 | 十月惊奇前后 | 各种波动 |
| 2024-11-05 | 选举日 | 价格趋近 0 或 1 |

---

## 资源

### 成员 B 提供的接口
- `core_analysis/db_interface.py` — 所有数据库读写操作
- `core_analysis/zscore_detector.py` — Z-Score 骨架
- `core_analysis/whale_alert.py` — Whale Alert 骨架

### API 端点（可能需要用）
- Polymarket CLOB API: `https://clob.polymarket.com`
  - `/trades` — 交易记录（需用于 Benford + Whale）
  - `/prices-history` — 价格历史（已被 B 集成）
- Polymarket Gamma API: `https://gamma-api.polymarket.com`
  - `/events` — 市场元数据

### 依赖库
- pandas, numpy — 数据处理
- scipy.stats — 卡方检验（Benford's Law）
- matplotlib/plotly — 可视化
- jupyter — Notebook 展示

---

*Update this file after every 2 view/browser/search operations*
