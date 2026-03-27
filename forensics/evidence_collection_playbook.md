# PolyWatch Evidence Collection Playbook (Member D)

本手册用于把 `case_study_001/002/003.md` 从模板升级为最终可提交稿。

## 1. 目标与产出

你需要为每个 Case 补齐三类证据：

1. **交易哈希链路表**（source -> relay -> target）
2. **告警与链上时间同步表**（alert time vs tx time）
3. **证据评分与最终判定**（TP/FP/UNRESOLVED）

对应模板文件：

- `forensics/case_001_evidence_template.csv`
- `forensics/case_002_evidence_template.csv`
- `forensics/case_003_evidence_template.csv`

## 2. 推荐采集顺序（最省时）

按以下顺序做，每个 case 约 20-40 分钟：

1. 从 `alerts_to_verify.csv` 选出该 case 的 2-5 个重点告警（高 severity 优先）
2. 在浏览器（Polygonscan/Etherscan）定位目标地址与上游来源地址
3. 记录 3-8 条关键交易（至少覆盖 source/relay/entry）
4. 回填 CSV 模板
5. 在 case study 中同步评分与最终结论

## 3. 字段填写规范

### 3.1 交易哈希字段

- `tx_hash`: 必须完整（0x...）
- `block_time_utc`: 统一 UTC，格式 `YYYY-MM-DD HH:MM:SS`
- `amount_usdc`: 仅填数值，不带单位（例如 `580.0`）
- `leg_type`: `source_funding` / `relay_transfer` / `market_entry`

### 3.2 时间同步字段

- `alert_time_utc`: 取自告警时间（统一转 UTC）
- `tx_time_utc`: 对应交易时间（UTC）
- `delta_minutes`: `tx_time - alert_time`（分钟，可正可负）
- `sync_interpretation`:
  - `tight_sync`（|delta| <= 10）
  - `moderate_sync`（10 < |delta| <= 60）
  - `weak_sync`（|delta| > 60）

### 3.3 证据评分字段（1-5）

- `timeline_alignment_score`
- `topology_suspicion_score`
- `public_event_alternative_score`（分数越高表示“有更强公共事件替代解释”）
- `attribution_confidence_score`

## 4. 判定规则（建议）

先计算：

`manipulation_score = timeline_alignment + topology_suspicion + attribution_confidence - public_event_alternative`

建议阈值：

- `>= 8`：倾向 `TRUE_POSITIVE`
- `5 ~ 7`：`UNRESOLVED`
- `<= 4`：倾向 `FALSE_POSITIVE`

> 注意：这是工程化建议，不替代人工审阅。若出现强冲突证据，人工判定优先。
> 备注：上述分数可按“单条腿”先打草案分，最终 `proposed_label` 按“整案（case-level）”综合决定；若链上归因证据不足，可保留 `UNRESOLVED`。

## 5. 最终提交前检查清单

- [ ] 每个 case 至少 3 条交易哈希
- [ ] 每个 case 至少 2 条 alert-vs-tx 时间同步记录
- [ ] 每个 case 四项评分均已填写并给出理由
- [ ] 最终标签（TP/FP/UNRESOLVED）与理由一致
- [ ] case 文档中引用的图、CSV、报告路径全部存在

## 6. 当前模板预填状态（2026-03-28）

为减少重复劳动，`case_001/002/003_evidence_template.csv` 已完成“结构化预填”：

- 已补齐每条腿（source/relay/entry）的 `amount_usdc`
- 已映射 `alert_id` 与 `alert_time_utc`（来源：priority queue）
- 已给出初始 `proposed_label` 与评分草案（用于人工复核起点）

仍需人工补齐的关键字段：

- `tx_hash`
- `block_time_utc`
- `tx_time_utc`
- `delta_minutes`
- `sync_interpretation`

说明：预填标签仅用于“先验分诊”，最终提交结论以链上浏览器证据与人工复核为准。
