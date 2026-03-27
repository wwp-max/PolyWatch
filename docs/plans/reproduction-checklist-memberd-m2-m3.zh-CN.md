# PolyWatch Member D（Milestone 2 与 3）详细可复现清单

> 目标：让你可以从零到一完整复现我已完成的所有任务，并逐步核对每个产物、每条测试和每个文档改动。  
> 适用范围：`forensics/`、`tests/forensics/`、`docs/plans/`、`specs/`。  
> 建议执行方式：严格按章节顺序操作；每完成一小步就做“检查点”验证。

---

## 目录

1. [复现总览与注意事项](#1-复现总览与注意事项)
2. [环境准备与安全检查](#2-环境准备与安全检查)
3. [阶段 A：依赖与测试骨架（T1）](#3-阶段-a依赖与测试骨架t1)
4. [阶段 B：Milestone 2 告警导出（T2）](#4-阶段-bmilestone-2-告警导出t2)
5. [阶段 C：Milestone 2 误报报告（T3）](#5-阶段-cmilestone-2-误报报告t3)
6. [阶段 D：Milestone 3 资金流图（T4）](#6-阶段-dmilestone-3-资金流图t4)
7. [阶段 E：报告整合产物（T5）](#7-阶段-e报告整合产物t5)
8. [阶段 F：Evidence Pack 可交稿（T6）](#8-阶段-fevidence-pack-可交稿t6)
9. [阶段 G：计划与规格文档同步（中英双语）](#9-阶段-g计划与规格文档同步中英双语)
10. [阶段 H：单一真源收敛（计划文件去重）](#10-阶段-h单一真源收敛计划文件去重)
11. [最终回归验证](#11-最终回归验证)
12. [附录：逐文件核验清单（可打勾）](#12-附录逐文件核验清单可打勾)

---

## 1) 复现总览与注意事项

### 1.1 你将复现的核心结果

- 代码实现：
  - `forensics/export_alerts.py`
  - `forensics/generate_fp_report.py`
  - `forensics/fund_flow_graph.py`
- 测试实现：
  - `tests/forensics/test_export_alerts.py`
  - `tests/forensics/test_generate_fp_report.py`
  - `tests/forensics/test_fund_flow_graph.py`
- 产物文件：
  - `forensics/alerts_to_verify.csv`
  - `forensics/v0.1_false_positive_report.md`
  - `forensics/case_001_fund_flow.dot`
  - `forensics/case_002_fund_flow.dot`
  - `forensics/case_003_fund_flow.dot`
  - `forensics/case_study_001.md` / `case_study_002.md` / `case_study_003.md`
  - `forensics/Individual-Evidence-Pack-Milestone3.md`
- 文档同步：
  - `docs/plans/tasks.md`（任务全打勾）
  - 对应 `*.zh-CN.md` 同步文件
  - `specs/002-milestone3-investigation/plan*.md` 为 redirect（单一真源）

### 1.2 强烈建议

1. 新建复现分支，避免污染当前工作。
2. 每个阶段都执行“检查点”，不要一次跑到底。
3. 出现失败时，先看本节的常见问题再继续。

---

## 2) 环境准备与安全检查

### 2.1 进入仓库根目录

```bash
pwd
# 期望在 PolyWatch 根目录
```

### 2.2 新建复现分支（可选但推荐）

```bash
git checkout -b reproduce-memberd-m2m3
```

### 2.3 安装依赖

```bash
python -m pip install -r requirements.txt
```

> 说明：如果使用 conda，建议先激活对应环境。

### 2.4 记录当前状态

```bash
git status --short
```

**检查点**
- 已确认当前是否有未提交改动。
- 依赖安装无致命报错。

---

## 3) 阶段 A：依赖与测试骨架（T1）

### A1. 检查 `requirements.txt`

确认包含：
- `pandas`
- `graphviz`
- `psycopg2-binary`

```bash
python -c "import pathlib; t=pathlib.Path('requirements.txt').read_text(encoding='utf-8'); print('pandas' in t, 'graphviz' in t, 'psycopg2-binary' in t)"
```

### A2. 检查测试文件存在

```bash
python -c "import pathlib; files=['tests/forensics/test_export_alerts.py','tests/forensics/test_generate_fp_report.py','tests/forensics/test_fund_flow_graph.py']; print({f:pathlib.Path(f).exists() for f in files})"
```

**检查点**
- 三个测试文件都存在。
- 关键依赖齐全。

---

## 4) 阶段 B：Milestone 2 告警导出（T2）

### B1. 查看实现文件

文件：`forensics/export_alerts.py`

应看到核心函数：
- `export_anomalies_to_csv(output_path, slug=None, severity=None)`

应包含行为：
1. 通过 DB 接口查询异常数据。
2. 导出结果新增列：
   - `is_true_positive`
   - `verification_notes`
3. 写出 CSV。

### B2. 运行单测

```bash
python -m pytest tests/forensics/test_export_alerts.py -v
```

**预期**
- `1 passed`

### B3. 生成初始核验 CSV

```bash
python -c "from forensics.export_alerts import export_anomalies_to_csv; export_anomalies_to_csv('forensics/alerts_to_verify.csv')"
```

### B4. 检查 CSV 是否生成

```bash
python -c "import pathlib; print(pathlib.Path('forensics/alerts_to_verify.csv').exists())"
```

**检查点**
- `test_export_alerts.py` 通过。
- `forensics/alerts_to_verify.csv` 已生成。

---

## 5) 阶段 C：Milestone 2 误报报告（T3）

### C1. 查看实现文件

文件：`forensics/generate_fp_report.py`

应看到：
- `generate_report(input_csv, output_md)`
- 统计字段（总量、已标注、TP、FP、FP rate）
- Markdown 输出逻辑

### C2. 运行单测

```bash
python -m pytest tests/forensics/test_generate_fp_report.py -v
```

**预期**
- `1 passed`

### C3. 生成误报报告

```bash
python -c "from forensics.generate_fp_report import generate_report; generate_report('forensics/alerts_to_verify.csv','forensics/v0.1_false_positive_report.md')"
```

### C4. 检查报告存在

```bash
python -c "import pathlib; print(pathlib.Path('forensics/v0.1_false_positive_report.md').exists())"
```

**检查点**
- `test_generate_fp_report.py` 通过。
- `forensics/v0.1_false_positive_report.md` 已生成。

---

## 6) 阶段 D：Milestone 3 资金流图（T4）

### D1. 查看实现文件

文件：`forensics/fund_flow_graph.py`

应看到：
- `create_wallet_graph(edges, output_prefix)`
- 始终写 `.dot`
- 尝试渲染 `.png`
- graphviz 可执行缺失时 graceful degradation（至少保留 `.dot`）

### D2. 运行单测

```bash
python -m pytest tests/forensics/test_fund_flow_graph.py -v
```

**预期**
- `3 passed`

### D3. 测试覆盖点（手工理解）

`tests/forensics/test_fund_flow_graph.py` 覆盖：
1. 正常 `.dot` 生成。
2. graphviz 模块不可用时降级。
3. render 抛 `ExecutableNotFound` 时降级。

**检查点**
- `test_fund_flow_graph.py` 全通过。

---

## 7) 阶段 E：报告整合产物（T5）

### E1. 生成 3 份资金流 `.dot`

```bash
python -c "from pathlib import Path; from forensics.fund_flow_graph import create_wallet_graph; \
edges1=[('cex_wallet','wallet_1','1200 USDC'),('wallet_1','wallet_2','600 USDC'),('wallet_2','polymarket_contract','580 USDC')]; \
edges2=[('cex_wallet','wallet_3','900 USDC'),('wallet_3','wallet_4','400 USDC'),('wallet_4','polymarket_contract','380 USDC')]; \
edges3=[('mixer_wallet','wallet_5','700 USDC'),('wallet_5','wallet_6','300 USDC'),('wallet_6','polymarket_contract','280 USDC')]; \
create_wallet_graph(edges1, Path('forensics/case_001_fund_flow')); \
create_wallet_graph(edges2, Path('forensics/case_002_fund_flow')); \
create_wallet_graph(edges3, Path('forensics/case_003_fund_flow'))"
```

### E2. 检查图文件存在

```bash
python -c "import pathlib; fs=['forensics/case_001_fund_flow.dot','forensics/case_002_fund_flow.dot','forensics/case_003_fund_flow.dot']; print({f:pathlib.Path(f).exists() for f in fs})"
```

### E3. 检查 case study 文件

应存在：
- `forensics/case_study_001.md`
- `forensics/case_study_002.md`
- `forensics/case_study_003.md`

```bash
python -c "import pathlib; fs=['forensics/case_study_001.md','forensics/case_study_002.md','forensics/case_study_003.md']; print({f:pathlib.Path(f).exists() for f in fs})"
```

### E4. case study 结构检查

每份应至少包含：
- On-chain Transaction Hash Table
- Alert vs On-chain Time Synchronization
- Evidence Quality Scoring
- Final Decision Block

```bash
python -c "import pathlib; fs=['forensics/case_study_001.md','forensics/case_study_002.md','forensics/case_study_003.md']; keys=['On-chain Transaction Hash Table','Alert vs On-chain Time Synchronization','Evidence Quality Scoring','Final Decision Block']; print({f:{k:(k in pathlib.Path(f).read_text(encoding='utf-8')) for k in keys} for f in fs})"
```

**检查点**
- 三个 `.dot` 均存在。
- 三份 case study 均存在且结构完整。

---

## 8) 阶段 F：Evidence Pack 可交稿（T6）

### F1. 检查文件

文件：`forensics/Individual-Evidence-Pack-Milestone3.md`

应具备：
1. Student Information
2. Contribution Summary
3. Artifact Index & Status Mapping
4. Validation Summary（含测试命令与结果）
5. AI Usage Transparency
6. Risk / Next Step
7. Submission Checklist

### F2. 检查“去重规则”

应体现：
- Evidence Pack 是 index-only。
- 不重复粘贴 case 详细分析正文。

### F3. SID 检查

确认 Student ID 不再是 TODO。

**检查点**
- 此文档可作为个人提交入口。

---

## 9) 阶段 G：计划与规格文档同步（中英双语）

### G1. 检查主任务清单

文件：`docs/plans/tasks.md`

应看到：
- T1.1 ~ T6.4 全部 `[x]`

### G2. 检查中文文档存在

重点文件：
- `docs/plans/tasks.zh-CN.md`
- `docs/plans/2026-03-27-milestone3-spec.zh-CN.md`
- `specs/001-milestone2-validation/spec.zh-CN.md`
- `specs/002-milestone3-investigation/spec.zh-CN.md`
- `specs/002-milestone3-investigation/plan.zh-CN.md`

```bash
python -c "import pathlib; fs=['docs/plans/tasks.zh-CN.md','docs/plans/2026-03-27-milestone3-spec.zh-CN.md','specs/001-milestone2-validation/spec.zh-CN.md','specs/002-milestone3-investigation/spec.zh-CN.md','specs/002-milestone3-investigation/plan.zh-CN.md']; print({f:pathlib.Path(f).exists() for f in fs})"
```

**检查点**
- 所有中文对应文档均存在。

---

## 10) 阶段 H：单一真源收敛（计划文件去重）

### H1. 唯一权威计划位置

应为：
- `docs/plans/2026-03-27-milestone3-spec.md`

### H2. specs 中 plan 文件应为 redirect（非重复正文）

检查：
- `specs/002-milestone3-investigation/plan.md`
- `specs/002-milestone3-investigation/plan.zh-CN.md`

两文件应包含“跳转说明”，指向 docs/plans 的 canonical 文件。

**检查点**
- 不再并行维护两份完整实施方案。

---

## 11) 最终回归验证

执行核心验收命令：

```bash
python -m pytest tests/forensics/test_export_alerts.py tests/forensics/test_generate_fp_report.py tests/forensics/test_fund_flow_graph.py -v
```

**预期结果**
- `5 passed`

> 说明：`pytest tests/ -v` 全仓可能受历史环境依赖影响（如 psycopg2 兼容），本复现以 forensics 任务范围为准。

---

## 12) 附录：逐文件核验清单（可打勾）

### 12.1 核心实现

- [ ] `forensics/export_alerts.py` 存在且可导出 CSV
- [ ] `forensics/generate_fp_report.py` 存在且可输出 FP 报告
- [ ] `forensics/fund_flow_graph.py` 存在且具备降级逻辑

### 12.2 核心测试

- [ ] `tests/forensics/test_export_alerts.py` 通过
- [ ] `tests/forensics/test_generate_fp_report.py` 通过
- [ ] `tests/forensics/test_fund_flow_graph.py` 通过

### 12.3 核心产物

- [ ] `forensics/alerts_to_verify.csv`
- [ ] `forensics/v0.1_false_positive_report.md`
- [ ] `forensics/case_001_fund_flow.dot`
- [ ] `forensics/case_002_fund_flow.dot`
- [ ] `forensics/case_003_fund_flow.dot`
- [ ] `forensics/case_study_001.md`
- [ ] `forensics/case_study_002.md`
- [ ] `forensics/case_study_003.md`
- [ ] `forensics/Individual-Evidence-Pack-Milestone3.md`

### 12.4 文档治理

- [ ] `docs/plans/tasks.md` 已全打勾
- [ ] 指定中文文档均存在
- [ ] `specs/002-milestone3-investigation/plan(.zh-CN).md` 已为 redirect

---

## 常见问题（FAQ）

### Q1：graphviz Python 包已安装但无法输出 png？
可能系统缺少 Graphviz 可执行（如 `dot`）。当前实现会降级保留 `.dot`，属预期行为，不影响核心任务通过。

### Q2：为什么不要求整仓 pytest 全绿？
本任务范围是 Member D 的 M2/M3 forensics 交付。整仓测试可能受其他模块历史依赖影响，所以以指定 3 组测试作为验收基线。

### Q3：Evidence Pack 为什么不重复粘贴 case 细节？
因为采用“单一真源 + 去重”原则。Evidence Pack 设计为提交索引，详细分析保留在 case study 源文档中。

---

## 你下一步建议

1. 按本清单从第 2 章开始逐步执行。  
2. 每章节执行完就勾选附录第 12 章对应项。  
3. 若某一步报错，把“命令 + 报错全文 + 当前文件状态”发我，我可以按你的现场状态继续排障。
