# Task Plan — 成员 C：核心算法工程师 (Quant / Core Logic)

## Goal
为 PolyWatch 构建完整的异常检测算法引擎：实现 Z-Score、Benford's Law、Whale Alert 三大算法，使用 2024 年大选数据完成回测验证，输出 Jupyter Notebooks + Python 脚本 + 准确率报告。

## Current Phase
Phase 0（规划完成，待启动 Phase 1）

---

## Phases

### Phase 0: 需求理解与规划
- [x] 分析成员 B 代码库
- [x] 理解可用数据和接口
- [x] 识别数据缺口（交易量、单笔交易数据）
- [x] 头脑风暴算法设计
- [x] 创建规划文件
- **Status:** complete

### Phase 1: Z-Score / 移动平均线策略（有数据，可立即开始）
- [ ] 重构 `zscore_detector.py`：多窗口、EWMA、动态阈值
- [ ] 添加价格变化率（delta / return rate）异常检测
- [ ] 用 2024 大选数据跑全量检测
- [ ] 可视化检测结果（价格曲线 + 异常标注）
- [ ] 将结果写入 `anomaly_events` 表
- [ ] 写 Jupyter Notebook 展示
- [ ] 写单元测试
- **Status:** pending
- **预计文件：**
  - `core_analysis/zscore_detector.py`（重构）
  - `notebooks/01_zscore_analysis.ipynb`
  - `tests/core_analysis/test_zscore_detector.py`

### Phase 2: Benford's Law 检验
- [ ] 研究 Polymarket CLOB API `/trades` 端点获取交易数据
- [ ] 如果交易数据可获取：用真实交易量做 Benford 检验
- [ ] 如果交易数据不可获取：用价格变化幅度做 MVP 版本
- [ ] 实现 Benford 分布计算 + 卡方检验
- [ ] 支持分时段检验（滑动窗口 Benford 检验）
- [ ] 可视化：实际分布 vs 理论 Benford 分布对比图
- [ ] 写 Jupyter Notebook 展示
- [ ] 写单元测试
- **Status:** pending
- **预计文件：**
  - `core_analysis/benford_detector.py`（新建）
  - `notebooks/02_benford_analysis.ipynb`
  - `tests/core_analysis/test_benford_detector.py`

### Phase 3: 鲸鱼警报 (Whale Alert)
- [ ] 研究获取单笔交易数据的途径（CLOB API / The Graph）
- [ ] 重构 `whale_alert.py`：单笔大额 + 累计大额 + 方向偏向
- [ ] 实现价格影响分析（大额交易前后价格变化）
- [ ] 可视化：大额交易时间线 + 价格叠加图
- [ ] 写 Jupyter Notebook 展示
- [ ] 写单元测试
- **Status:** pending
- **预计文件：**
  - `core_analysis/whale_alert.py`（重构）
  - `notebooks/03_whale_alert_analysis.ipynb`
  - `tests/core_analysis/test_whale_alert.py`

### Phase 4: 回测系统 + 准确率验证
- [ ] 构建回测框架（Backtester 类）
- [ ] 手动标注 2024 大选重大事件时间线
- [ ] 对每个算法跑全量回测
- [ ] 参数网格搜索（window, threshold 组合优化）
- [ ] 计算评估指标：Precision, Recall, F1-Score, FP Rate, FN Rate
- [ ] 生成 ROC 曲线
- [ ] 输出准确率验证报告（Markdown + Notebook）
- **Status:** pending
- **预计文件：**
  - `core_analysis/backtester.py`（新建）
  - `notebooks/04_backtest_report.ipynb`
  - `docs/algorithm-accuracy-report.md`

### Phase 5: 整合 + 统一运行入口
- [ ] 创建统一的 `run_analysis.py` 脚本（一键跑所有算法）
- [ ] 确保所有异常结果写入 `anomaly_events` 表
- [ ] 确保成员 E 前端能正确读取结果
- [ ] 所有测试通过
- [ ] 最终文档整理
- **Status:** pending
- **预计文件：**
  - `core_analysis/run_analysis.py`（新建）
  - `core_analysis/README.md`（更新）

---

## 依赖关系与优先级

```
Phase 1 (Z-Score) ──────→ 可立即开始（数据已就绪）
Phase 2 (Benford) ──────→ 需先调研交易量数据来源
Phase 3 (Whale Alert) ──→ 需先调研单笔交易数据来源
Phase 4 (回测) ─────────→ 依赖 Phase 1-3 的算法实现
Phase 5 (整合) ─────────→ 依赖 Phase 1-4 全部完成
```

**推荐执行顺序：Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5**
（Phase 2 和 Phase 3 可以并行研究数据来源）

---

## Key Questions

1. **交易量数据从哪来？** Benford 和 Whale Alert 都需要交易数据，B 的管道目前只有价格。需要调研 CLOB API `/trades` 端点或 The Graph subgraph。
2. **如何定义"异常"vs"正常事件导致的波动"？** 2024 大选中有很多真实事件导致价格剧烈变化（如 Biden 退选），这些不是操纵。回测标注是关键。
3. **算法参数怎么选？** 需要通过网格搜索和回测来确定最优参数，不能凭感觉。
4. **成员 E 前端需要什么格式？** anomaly_events 表的 detail 字段（JSONB）里应该放什么信息？需要和 E 确认。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Phase 1 (Z-Score) 优先 | 价格数据已齐全，可以立即产出成果 |
| Benford 先做价格变化量 MVP | 交易量数据暂缺，先出原型后补数据 |
| 回测用 2024 大选数据 | 7356 条，跨度近 1 年，事件丰富，最适合验证 |
| 复用 B 的 db_interface | 不重复造轮子，统一数据接口 |
| 输出 Notebook + Script 双份 | Notebook 展示给人看，Script 供生产调用 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| (暂无) | - | - |

## Notes
- Update phase status as you progress: pending → in_progress → complete
- Re-read this plan before major decisions
- Log ALL errors - they help avoid repetition
- 成员 B 的数据库连接：`postgresql://polywatch:polywatch@localhost:5433/polywatch`
- 环境变量：`DATABASE_URL=postgresql://polywatch:polywatch@localhost:5433/polywatch`
