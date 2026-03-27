# 功能规格：Milestone 3 调查（案例研究）

**特性分支**：`002-milestone3-investigation`  
**创建日期**：2026-03-27  
**状态**：Draft  
**输入**：用户需求「完成操纵事件的深度调查报告与案例研究」

## 用户场景与测试（必填）

### 用户故事 1 - Etherscan / Polygonscan 交易链路追踪（优先级：P1）

作为安全研究员（成员 D），我希望追踪成员 C 的聚类/Sybil 算法标记出的高可疑账户的资金来源与交易链路。

**优先级原因**：这是深度取证（+5% bonus）的基础，用于实证操纵行为。

**独立测试**：在 Polygonscan 上手工核验一个可疑地址并定位其初始资金来源（如 CEX 或 Mixer）。

**验收场景**：

1. **Given** 一组可疑钱包，**When** 查询其交易历史，**Then** 可追溯到初始资金来源。
2. **Given** 已知资金来源，**When** 其与 Tornado Cash 或多个钱包相同 CEX 提现相关联，**Then** 可作为 Sybil 集群证据。

---

### 用户故事 2 - GraphViz 钱包关联可视化（优先级：P2）

作为安全研究员，我希望绘制可疑钱包之间的资金互动图，以更直观地呈现攻击路径。

**优先级原因**：图形化表达对最终展示非常关键。

**独立测试**：生成 GraphViz `.dot` 并渲染为 `.png`，图中应展示钱包间边关系。

**验收场景**：

1. **Given** 一组集群钱包之间交易，**When** 运行图生成脚本，**Then** 产出连接钱包与目标 Polymarket 合约的可视化图。

---

### 用户故事 3 - 最终案例报告生成（优先级：P1）

作为安全研究员，我希望将交易追踪、资金来源分析、外部事件验证与算法告警整合为完整的 Markdown 案例报告。

**优先级原因**：这是 Milestone 3 的核心交付物。

**独立测试**：依据项目评分标准审阅最终 `case_study_00X.md`。

**验收场景**：

1. **Given** 已收集完整取证证据，**When** 我汇总报告，**Then** 报告应清晰论证该事件是自然市场波动还是 Sybil/Whale 操纵。

---

### 用户故事 4 - 个人证据包提交（优先级：P1）

作为安全研究员（成员 D），我希望将 Milestone 2 与 3 的交付物汇总到 `forensics/Individual-Evidence-Pack-Milestone3.md`，以“提交索引”形式形成可审计且完整的提交包，同时避免重复报告内容。

**优先级原因**：这是面向评分的最终提交工件，体现完成度与可追溯性。

**独立测试**：审阅 `forensics/Individual-Evidence-Pack-Milestone3.md`，确认所有必需工件均有链接和状态映射，详细分析仍保留在原 case/report 文件中。

**验收场景**：

1. **Given** M2/M3 产物已生成，**When** 构建 Evidence Pack，**Then** 其包含 FP 报告、案例报告与资金流图链接。
2. **Given** 证据细节已在 case/report 中存在，**When** 完成 Evidence Pack，**Then** 仅链接而不重复整段分析表与正文内容。

## 需求（必填）

### 功能需求

- **FR-001**：系统必须输出成员 C 的 Sybil 检测标记地址。
- **FR-002**：研究员必须使用区块浏览器（Polygonscan/Etherscan）或 Graph API 拉取历史余额与转账。
- **FR-003**：系统必须提供恶意资金流可视化。
- **FR-004**：最终报告必须包含至少 3 个不同操纵强度的案例研究。
- **FR-005**：研究员必须产出 `forensics/Individual-Evidence-Pack-Milestone3.md`，并以索引式（引用而非复制）方式汇总 M2/M3 证据工件。

### 关键实体

- **Sybil Cluster**：由同一来源资金支持、行为一致的一组动态钱包。
- **Fund Flow Graph**：展示 USDC 从来源到 Polymarket CLOB 路径的有向无环图（DAG）。

## 成功标准（必填）

### 可度量结果

- **SC-001**：在 `forensics` 中生成 3~5 份完整案例 Markdown 报告。
- **SC-002**：至少 1 份案例识别到此前未验证或高度可疑的操纵尝试。
- **SC-003**：报告包含交易哈希、时间同步分析、资金来源图等具体证据。
- **SC-004**：`forensics/Individual-Evidence-Pack-Milestone3.md` 包含工件链接、工件状态映射和提交检查清单；详细证据保留在被引用源报告中。

## 假设

- Etherscan / Polygonscan API 或网页可用，且不会因限流阻断必要查询。
- 成员 C 的聚类算法已识别出至少一批可调查候选钱包。
