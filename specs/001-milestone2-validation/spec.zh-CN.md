# 功能规格：Milestone 2 验证（误报率）

**特性分支**：`001-milestone2-validation`  
**创建日期**：2026-03-27  
**状态**：Draft  
**输入**：用户需求「验证 v0.1 告警结果并报告误报率」

## 用户场景与测试（必填）

### 用户故事 1 - 获取告警历史（优先级：P1）

作为安全研究员（成员 D），我希望从数据库中获取 v0.1 算法（如 Z-Score、Whale Alert）生成的历史告警，以便获得可核验的数据集。

**优先级原因**：这是第一步，没有告警数据就无法核验。

**独立测试**：通过查询 PostgreSQL 的 `anomalies` 表，确认给定 market slug 的事件能正确返回。

**验收场景**：

1. **Given** core_analysis 已将 v0.1 异常写入数据库，**When** 我通过 `query_anomalies(slug)` 查询，**Then** 我能得到带时间戳的异常事件列表。

---

### 用户故事 2 - 人工与半自动核验（优先级：P1）

作为安全研究员，我希望将每条告警与公开新闻事件和链上浏览器数据进行交叉核对，以判断该告警是真实操纵还是外部事件导致的正常市场反应。

**优先级原因**：这是 Milestone 2 的核心，必须区分真阳性与误报。

**独立测试**：选取 10 条历史告警并基于外部数据成功标注为 TRUE_POSITIVE 或 FALSE_POSITIVE。

**验收场景**：

1. **Given** 告警显示价格突增，**When** 我查询该市场重大新闻时间线，**Then** 若可由重大新闻解释则标注为 FALSE_POSITIVE。
2. **Given** 告警无对应外部新闻，**When** 我分析交易资金流，**Then** 标注为潜在 TRUE_POSITIVE。

---

### 用户故事 3 - 误报反馈报告（优先级：P2）

作为安全研究员，我希望计算 v0.1 算法误报率，并向核心算法工程师（成员 C）提供反馈以调整阈值。

**优先级原因**：闭环反馈是 Milestone 2 MVP 必需项，也是 +5% Spec-Driven 奖励关键。

**独立测试**：生成 Markdown 报告，汇总告警总数、误报数与 FP rate。

**验收场景**：

1. **Given** 告警数据已完整标注，**When** 我运行报告脚本，**Then** 会生成反馈报告（如 `v0.1_false_positive_report.md`）。

## 需求（必填）

### 功能需求

- **FR-001**：系统必须支持按时间窗口与市场维度，从 PolyWatch 数据库检索异常记录。
- **FR-002**：研究员必须建立可复现流程（人工或自动）为异常事件打 TP/FP 标签。
- **FR-003**：系统必须输出可量化的误报率（如 FP Rate = False Positives / Total Alerts）。

### 关键实体

- **Anomaly Event**：由 v0.1 算法触发并写入数据库的事件，包含时间戳、市场 slug、类型（如 `zscore_spike`）与严重度。
- **Verification Label**：成员 D 核验阶段附加在 Anomaly Event 上的布尔/分类标签。

## 成功标准（必填）

### 可度量结果

- **SC-001**：至少核验并标注 50 条 v0.1 告警（若总数不足 50，则全部完成）。
- **SC-002**：计算并记录明确的误报率百分比。
- **SC-003**：向成员 C 提交反馈报告，说明常见误报原因（例如“新闻驱动波动尚未过滤”）。
- **SC-004**：Milestone 2 产物（`forensics/alerts_to_verify.csv`、`forensics/v0.1_false_positive_report.md`）需在 `forensics/Individual-Evidence-Pack-Milestone3.md` 中明确引用并总结。

## 假设

- `data_pipeline` 正在运行且数据库已有数据。
- 成员 C 已成功在数据集上运行 v0.1 算法。
- 可访问被分析市场的真实新闻时间线。
