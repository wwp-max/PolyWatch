# Milestone 2 与 3 取证实现计划

> **给 Claude 的说明：** 必须使用 superpowers:executing-plans 子技能按任务逐项执行。

**目标：** 构建核验流水线用于导出告警并计算误报率（Milestone 2），并构建 GraphViz 资金流可视化以生成深度案例（Milestone 3）。

**架构：** 在 `forensics` 模块中创建 Python 脚本，通过 `core_analysis.db_interface` 访问 PostgreSQL 导出异常；再基于人工标注数据生成误报报告；最后集成 `graphviz` 生成钱包资金流图并用于最终案例。

**技术栈：** Python 3、Pandas、Graphviz、Pytest、unittest.mock

---

### 任务 1：Milestone 2 - 告警核验导出器

**文件：**
- 新建：`forensics/export_alerts.py`
- 测试：`tests/forensics/test_export_alerts.py`

**步骤 1：先写失败测试**

在 `tests/forensics/test_export_alerts.py` 中实现 `test_export_anomalies_to_csv`，使用 mock DataFrame 并断言导出 CSV 包含：
- `is_true_positive`
- `verification_notes`

**步骤 2：运行测试，确认先失败**

运行：`python -m pytest tests/forensics/test_export_alerts.py -v`  
预期：`ModuleNotFoundError`

**步骤 3：实现最小功能**

在 `forensics/export_alerts.py` 中：
- 调用 `query_anomalies()` 拉取数据
- 若为空则初始化标准列
- 增加人工标注列
- 导出到 CSV

**步骤 4：再次运行测试，确认通过**

运行：`python -m pytest tests/forensics/test_export_alerts.py -v`  
预期：PASS

---

### 任务 2：Milestone 2 - 误报率报告生成器

**文件：**
- 新建：`forensics/generate_fp_report.py`
- 测试：`tests/forensics/test_generate_fp_report.py`

**步骤 1：先写失败测试**

在 `tests/forensics/test_generate_fp_report.py`：
- 构造 TP/FP/未标注样本 CSV
- 调用 `generate_report(...)`
- 断言统计值与输出 Markdown 内容

**步骤 2：运行测试，确认先失败**

运行：`python -m pytest tests/forensics/test_generate_fp_report.py -v`  
预期：`ModuleNotFoundError`

**步骤 3：实现最小功能**

在 `forensics/generate_fp_report.py`：
- 读取 CSV
- 统计总量、已标注、TP、FP、FP rate
- 输出 Markdown 报告

**步骤 4：再次运行测试，确认通过**

运行：`python -m pytest tests/forensics/test_generate_fp_report.py -v`  
预期：PASS

---

### 任务 3：Milestone 3 - GraphViz 依赖准备

**文件：**
- 修改：`requirements.txt`

**步骤 1：补充依赖并安装**

- 在 `requirements.txt` 增加 `graphviz`
- 安装：`pip install -r requirements.txt`

---

### 任务 4：Milestone 3 - 资金流图生成器

**文件：**
- 新建：`forensics/fund_flow_graph.py`
- 测试：`tests/forensics/test_fund_flow_graph.py`

**步骤 1：先写失败测试**

在 `tests/forensics/test_fund_flow_graph.py`：
- 构造 sample edges
- 调用 `create_wallet_graph(...)`
- 断言 `.dot` 文件存在且包含关键节点与标签

**步骤 2：运行测试，确认先失败**

运行：`python -m pytest tests/forensics/test_fund_flow_graph.py -v`  
预期：`ModuleNotFoundError`

**步骤 3：实现最小功能**

在 `forensics/fund_flow_graph.py`：
- 用 `graphviz.Digraph` 构图
- 保存 `.dot`
- 尝试渲染（`.png`）
- 若系统缺少 graphviz 可执行，优雅降级（只保留 `.dot`）

**步骤 4：再次运行测试，确认通过**

运行：`python -m pytest tests/forensics/test_fund_flow_graph.py -v`  
预期：PASS

---

### 任务 5：Milestone 3 - 个人证据包最终整理

**文件：**
- 创建/更新：`forensics/Individual-Evidence-Pack-Milestone3.md`
- 引用工件：`forensics/alerts_to_verify.csv`、`forensics/v0.1_false_positive_report.md`、`forensics/case_study_001.md`、`forensics/case_study_002.md`、`forensics/case_study_003.md`、`forensics/case_00X_fund_flow.dot/.png`

> **去重规则：** 本任务仅做打包与索引，不重复撰写已在 `case_study_00X.md` 中存在的详细分析表、交易表与时间线推理。

**步骤 1：构建证据包结构**

在 `forensics/Individual-Evidence-Pack-Milestone3.md` 中加入：
1. Milestone 2 证据摘要
2. Milestone 3 案例证据摘要
3. 工件索引与状态映射
4. 验证结果摘要
5. 最终提交清单

**步骤 2：填充链接与状态映射**

- 链接所有 `forensics/` 下实际产物
- 增加工件状态表（路径、用途、完整度、备注）
- 保证与 `v0.1_false_positive_report.md`、`case_study_00X.md` 的结论引用一致

**步骤 3：验证**

运行：

`python -m pytest tests/forensics/test_export_alerts.py tests/forensics/test_generate_fp_report.py tests/forensics/test_fund_flow_graph.py -v`

预期：PASS

**步骤 4：最终就绪检查**

- 被引用路径全部存在
- 证据包关键章节完整
- 教师提交要求已明确覆盖
