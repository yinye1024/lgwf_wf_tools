# LGWF Post-Run 自动分析与优化设计

## 目标

`lgwf-wf-post-run` 是一个独立的 LGWF 后处理 workflow skill，用于在业务 workflow 运行结束后，读取该次运行的结构化产物，生成运行诊断、优化建议和可审查的后续改进计划。

第一版目标是“分析和建议”，不自动修改业务 workflow。后续可以在人工确认后扩展为“生成 patch”或“应用 patch”。

## 设计原则

- `lgwf` runtime 继续保持确定性，只负责编译、执行、checkpoint、run record 和基础状态记录。
- `lgwf-client-assist` 继续作为统一 facade，提供运行、status、runs、changed files、checkpoint、doctor 等底层能力。
- `lgwf-wf-post-run` 作为上层 workflow，编排“收集运行上下文 -> 分析运行过程 -> 生成优化建议 -> 输出报告”。
- 默认不修改用户 workflow、prompt、script 或 workspace 业务文件。
- 所有分析结果写入当前后处理 workflow 的 `work_dir`，不污染被分析 workflow package。
- 自动优化建议必须可追溯到具体 run、node、日志片段或产物字段。

## 非目标

- 第一版不做自动 patch。
- 第一版不恢复或重跑失败 workflow。
- 第一版不替代 `lgwf-client-assist` 的 status、runs、doctor、resume 等能力。
- 第一版不尝试证明业务结果正确，只分析 workflow 执行质量、可维护性和可恢复性。
- 第一版不要求修改 `lgwf` runtime 内核。

## 使用场景

### 手动分析某次运行

用户已经有业务 workflow 的 `work_dir` 和 `run_id`，希望生成运行报告：

```powershell
python <lgwf-client-assist>\scripts\lgwf.py run `
  --workflow-lgwf D:\allen\github\lgwf_plugins\plugins\team-skills\skills\lgwf-wf-post-run\workflow.lgwf `
  --work-dir <post_run_work_dir> `
  --input-json "{""target_work_dir"":""<business_work_dir>"",""run_id"":""<run_id>""}"
```

### 业务 workflow 结束后自动触发

后续可以由 `lgwf-client-assist` 提供薄入口：

```powershell
lgwf.py run --workflow-lgwf <business_workflow> --work-dir <business_work_dir> --post-run-analyze
```

facade 在业务 workflow 完成后，启动 `lgwf-wf-post-run`，把 `target_work_dir`、`run_id`、`workflow_json`、`workflow_lgwf` 等信息作为输入传入。

## 输入契约

后处理 workflow 的 `input-json` 建议使用：

```json
{
  "target_work_dir": "D:\\path\\to\\business-work-dir",
  "run_id": "20260626T062350.806991+0000-9c7085c9",
  "workflow_json": "D:\\path\\to\\workflow.json",
  "workflow_lgwf": "D:\\path\\to\\workflow.lgwf",
  "workflow_root": "D:\\path\\to\\workflow-package",
  "analysis_level": "standard",
  "include_logs": true,
  "include_changed_files": true,
  "max_log_lines": 300,
  "max_file_preview_bytes": 20000
}
```

字段说明：

- `target_work_dir`：必选，被分析 workflow 的 `work_dir`。
- `run_id`：可选；缺省时读取 `target_work_dir` 的 latest run。
- `workflow_json`：可选；用于关联 runtime IR 和 node 配置。
- `workflow_lgwf`：可选；用于给出 DSL 层优化建议。
- `workflow_root`：可选；用于定位 prompt、script、workflow package。
- `analysis_level`：可选，`basic | standard | deep`，默认 `standard`。
- `include_logs`：可选，是否收集 progress log 和 stderr/stdout 摘要。
- `include_changed_files`：可选，是否读取 changed files manifest。
- `max_log_lines`：可选，限制日志上下文规模。
- `max_file_preview_bytes`：可选，限制文件预览规模。

## 输出契约

后处理 workflow 输出到自己的 `work_dir`：

```text
reports/
  run_context.json
  run_analysis.json
  optimization_suggestions.json
  post_run_report.md
```

### `run_context.json`

由脚本节点收集的事实数据，只做解析和裁剪，不做主观判断：

```json
{
  "target_work_dir": "...",
  "run_id": "...",
  "run_record": {},
  "checkpoint": {},
  "changed_files": {},
  "process_log_tail": [],
  "workflow_summary": {
    "entry_point": "confirm_plan_and_acceptance",
    "node_count": 12,
    "nodes": []
  },
  "available_artifacts": []
}
```

### `run_analysis.json`

由 Codex 节点生成的诊断结论：

```json
{
  "run_id": "...",
  "status": "completed",
  "overall_assessment": "stable",
  "findings": [
    {
      "severity": "medium",
      "category": "resume",
      "node_id": "apply_confirmed_contracts",
      "title": "失败节点可恢复信息完整",
      "evidence": ["checkpoint.failed_node=apply_confirmed_contracts"],
      "recommendation": "保留当前 checkpoint 策略。"
    }
  ],
  "risk_summary": {
    "side_effect_replay_risk": "low",
    "output_truncation_risk": "medium",
    "approval_routing_risk": "low"
  }
}
```

### `optimization_suggestions.json`

由 Codex 节点生成的改进建议，必须区分“建议”和“可自动化 patch”：

```json
{
  "suggestions": [
    {
      "id": "use-output-json-as-file",
      "priority": "high",
      "scope": "workflow",
      "target": "CODEX build_report",
      "summary": "大 JSON 输出建议使用 OUTPUT_JSON ... AS_FILE。",
      "rationale": "避免 stdout metadata 截断或日志膨胀。",
      "auto_patchable": true,
      "requires_approval": true
    }
  ],
  "next_actions": [
    "人工审查 high priority 建议。",
    "需要修改 workflow 时使用单独 apply workflow。"
  ]
}
```

### `post_run_report.md`

面向人的中文报告，包含：

- 运行概览
- 失败/等待/重跑节点摘要
- checkpoint 和 resume 可用性
- Codex 输出和 token 风险
- OUTPUT_JSON/AS_FILE 建议
- human approval route 建议
- changed files 摘要
- 高优先级优化建议
- 下一步操作

## 建议目录结构

```text
lgwf-wf-post-run/
  SKILL.md
  DESIGN.md
  workflow.lgwf
  agents/
    analyze_run.md
    suggest_optimizations.md
  scripts/
    collect_run_context.py
    write_report.py
  tests/
    test_collect_run_context.py
    test_write_report.py
  README.md
```

## Workflow 草案

```lgwf
WORKFLOW lgwf_post_run_analysis;

ENTRY collect_context;

PY collect_context
  SCRIPT "scripts/collect_run_context.py"
  RESULT state.run_context;

CODEX analyze_run
  PROMPT "agents/analyze_run.md"
  READ state.run_context
  OUTPUT_JSON "reports/run_analysis.json" AS_FILE;

CODEX suggest_optimizations
  PROMPT "agents/suggest_optimizations.md"
  READ state.run_context
  READ state.run_analysis
  OUTPUT_JSON "reports/optimization_suggestions.json" AS_FILE;

PY write_report
  SCRIPT "scripts/write_report.py"
  READ state.run_context
  READ state.run_analysis
  READ state.optimization_suggestions
  RESULT state.report;
```

说明：

- `collect_context` 只收集事实，不做优化判断。
- `analyze_run` 输出运行诊断 JSON。
- `suggest_optimizations` 输出优化建议 JSON。
- `write_report` 把两个 JSON 汇总成 `reports/post_run_report.md`。

## 分析维度

### 执行稳定性

- workflow 是否 completed、failed、waiting_human 或 stopped。
- 失败节点、失败类型、失败消息是否清晰。
- 是否存在重复失败节点。
- 是否有节点耗时异常。
- 是否存在未收敛的 react/agent loop。

### Checkpoint / Resume

- 是否存在 checkpoint。
- failed checkpoint 是否包含 `failed_node`、`current_node`、`state_before_current_node`。
- `workflow_hash` 是否匹配。
- 是否有 tmp checkpoint 残留。
- resume 是否可能从失败节点重新执行。

### 输出可靠性

- Codex 节点是否使用大 JSON stdout。
- 是否应切换为 `OUTPUT_JSON "..." AS_FILE`。
- JSON 输出是否被截断、缺字段或 parse 失败。
- 结果文件是否落在预期 workspace 路径。

### Human Approval

- approval 是否记录完整 response：`request_id`、`decision`、`comment`、`value`。
- 是否使用 `ROUTE_ON_DECISION`。
- reject/revise 是否有后续 route，而不是直接失败。
- 审批上下文是否足够让用户决策。

### Workflow 可维护性

- 节点职责是否过大。
- 是否缺少验收节点。
- prompt 是否缺少输出 schema。
- script/prompt 引用是否符合 package/resource 约束。
- 是否存在 package 和 work_dir 混用。

### 变更影响

- changed files 是否集中在预期目录。
- 是否有 `.lgwf`、临时文件、日志或 cache 被误写到 package。
- 是否有二进制或大文件意外生成。

## 与 `lgwf-client-assist` 的关系

第一阶段不要求修改 `lgwf-client-assist`。

第二阶段可以增加薄入口：

```powershell
lgwf.py post-run analyze --work-dir <target_work_dir> --run-id <run_id>
```

该入口只负责：

1. 定位 `lgwf-wf-post-run/workflow.lgwf`。
2. 创建独立后处理 `work_dir`。
3. 传入目标 workflow 的 `target_work_dir` 和 `run_id`。
4. 调用现有 `lgwf.py run`。

不要把分析逻辑写进 facade；facade 只做参数转发和路径解析。

## 后续自动优化流程

等第一版报告稳定后，新增第二个 workflow：

```text
lgwf_post_run_apply_suggestions
```

建议流程：

1. 读取 `optimization_suggestions.json`。
2. 过滤 `auto_patchable=true` 的建议。
3. 生成 patch plan。
4. `APPROVAL` 请求人工确认。
5. 确认后应用 patch。
6. 运行 `lgwf.py audit` 或目标 workflow smoke。

自动应用必须满足：

- 默认关闭。
- 必须有人类确认。
- patch 前后生成 diff。
- 不修改运行中的 `work_dir`。
- 只修改明确传入的 workflow package。

## 最小实现计划

1. 创建 `SKILL.md`、`workflow.lgwf`、`agents/`、`scripts/`、`tests/`。
2. 实现 `collect_run_context.py`，读取 run record、checkpoint、changed files、process log tail。
3. 编写 `analyze_run.md`，要求输出固定 JSON schema。
4. 编写 `suggest_optimizations.md`，要求建议必须给 evidence 和 priority。
5. 实现 `write_report.py`，生成中文 Markdown 报告。
6. 增加脚本单测，使用 fixtures 模拟 completed、failed、waiting_human 三类 run。
7. 使用 `lgwf-client-assist` 跑一个 shell smoke run，再用本 workflow 分析该 run。

## 验收标准

- 可以对 completed run 生成 `post_run_report.md`。
- 可以对 failed run 明确指出失败节点、失败原因和 resume 可用性。
- 缺少 checkpoint 或 run record 时输出清晰 warning，不崩溃。
- 大 JSON/Codex 输出风险可以被识别并建议 `AS_FILE`。
- human approval reject/revise route 风险可以被识别。
- 所有输出文件都在后处理 workflow 的 `work_dir/reports/` 下。
- 不修改被分析 workflow package。

## 风险与控制

- 风险：分析 prompt 过宽导致建议空泛。控制：prompt 强制 evidence、node_id、priority 和 actionable recommendation。
- 风险：日志或 changed files 太大。控制：脚本层裁剪，并在 `run_context.json` 记录裁剪信息。
- 风险：自动优化改坏 workflow。控制：第一版不自动 patch；第二版必须 approval。
- 风险：跨仓库路径混乱。控制：输入路径显式传入，脚本只读目标 `work_dir`，输出写当前 `work_dir`。

## 开放问题

- 是否需要 `lgwf-client-assist` 在每次 `run` 后自动提供 “运行分析命令提示”。
- 是否把 `run_context.json` 聚合能力下沉为 `lgwf.py runs collect-context`。
- `deep` 分析是否允许读取 prompt/script 全文，还是只读取摘要。
- 后续 patch workflow 是否与 `lgwf-wf-fix` 复用能力，避免重复实现修复逻辑。
