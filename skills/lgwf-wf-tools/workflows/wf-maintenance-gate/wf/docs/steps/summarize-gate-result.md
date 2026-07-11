# summarize-gate-result

## step_slug

`summarize-gate-result`

## step_name

汇总 gate 结论与维护报告

## goal

设计 `wf/06_summarize_gate_result/workflow.lgwf`，把变更上下文、影响分类、验证结果和失败路由合并成最终的 `maintenance_gate_summary.json` 与中文报告。这个阶段要把维护者真正关心的结论固定下来：当前能否继续打包、哪些检查失败、哪些检查被跳过、还建议转去哪个 workflow，以及关键产物都落在什么路径。

## inputs

- 上游阶段或节点：
  - `collect-change-context`
  - `classify-impact`
  - `run-verification`
  - `.lgwf/business_flow.json` 中 `06_summarize_gate_result` 阶段定义
- 依赖文件或状态：
  - `.lgwf/change_context.json`
  - `.lgwf/impact_classification.json`
  - `.lgwf/verification_results.json`
  - `.lgwf/failure_routes.json`
  - `docs_tmp/wf-maintenance-gate-development.md`
- 关键约束：
  - 最终状态必须限定为 `pass`、`fail` 或 `needs_review`
  - 报告正文默认使用中文
  - 总结阶段只做归并和呈现，不再执行验证命令

## outputs

- 预期生成的文件：
  - `wf/06_summarize_gate_result/workflow.lgwf`
  - `wf/06_summarize_gate_result/scripts/*.py`
  - `wf/06_summarize_gate_result/resources/*`
  - `.lgwf/maintenance_gate_summary.json`
  - `ws/reports/wf-maintenance-gate/report.md`
- 预期生成的目录：
  - `wf/06_summarize_gate_result/agents/`
  - `wf/06_summarize_gate_result/scripts/`
  - `wf/06_summarize_gate_result/resources/`
- 交付给下游的结构片段：
  - 总体 gate 状态
  - 已执行命令结果、失败项、关键产物和跳过原因摘要
  - 后续建议：是否可继续打包、是否需要人工复核、建议转入哪个 workflow

## dependencies

- 前置步骤：
  - `collect-change-context`
  - `classify-impact`
  - `run-verification`
- 依赖节点：
  - `verification_results` 与 `failure_routes`
  - 共享 helper 中的 status/route 枚举
- 需要人工确认的位置：
  - 当前阶段不新增人工确认

## implementation_suggestions

- 将“结构化 summary 计算”和“Markdown 报告渲染”拆成独立脚本，减少统计逻辑与文案拼接耦合。
- `maintenance_gate_summary.json` 应至少包含总体状态、输入请求摘要、影响分类摘要、已执行检查、失败项、关键产物路径和建议下一步。
- `report.md` 用维护者视角呈现：本次改动影响了什么、跑了哪些验证、哪些失败、为什么建议转到某个 workflow，以及是否建议再跑更高等级验证。
- 如果存在 package smoke、deep doctor 或 pre-release 跳过项，需要明确写出跳过原因，而不是只在命令列表里缺席。
- 资源目录中可以放报告模板、标题片段和状态文案映射，避免脚本硬编码大段 Markdown。

## 修订补充：状态归并与报告字段

`maintenance_gate_summary.json` 的最小结构：

```json
{
  "status": "pass",
  "risk": "medium",
  "input_summary": {},
  "impact_summary": {
    "categories": ["workflow_source"],
    "impacted_workflows": ["wf-create"],
    "ambiguities": []
  },
  "verification_summary": {
    "passed": ["doctor_basic"],
    "failed": [],
    "skipped": ["pre_release"],
    "stopped_early": false
  },
  "artifact_paths": [
    "ws/reports/wf-maintenance-gate/report.md"
  ],
  "failure_routes": [],
  "next_actions": [
    "可以继续本地维护流程；package smoke 未执行，发布前仍需显式确认。"
  ]
}
```

状态归并规则：

- 任一执行命令失败且 `failure_type` 非 `timeout`、`command_contract` 时，整体为 `fail`。
- 存在 `ambiguities`、zip 冲突未确认、命令契约异常、超时或高风险检查被跳过时，整体为 `needs_review`。
- 所有必需命令通过，且跳过项均有明确的 allow 开关原因时，整体为 `pass`。
- 仅 `docs_only` 且未执行命令时，可以为 `pass`，但报告必须说明未执行命令的原因。

`report.md` 必须包含以下中文小节：

- `结论`：`pass` / `fail` / `needs_review`、风险等级和一句话原因。
- `影响范围`：分类、受影响 workflow、歧义项。
- `验证执行`：命令、结果、耗时、跳过原因。
- `失败与路由`：失败类型、建议 workflow、理由。
- `产物路径`：summary、report、doctor/self-improve/package 相关产物。
- `后续动作`：是否可继续打包、是否需要更高等级验证、是否建议转入其他 workflow。

## acceptance_notes

- 重点确认总结阶段只读取既有 artifact，不再触发新的写入型维护动作。
- 重点确认无论部分命令失败还是被跳过，都能输出完整 `maintenance_gate_summary.json` 和 `report.md`。
- 重点确认报告不会出现“placeholder”“draft”这类初稿语气，除非是明确描述某个尚未执行的后续建议。
- 重点确认失败路由建议与实际失败类型一致，不会把 DSL 问题误导为 prompt 修复，或把治理问题误导为 workflow 实现修复。

## out_of_scope

- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 自动启动其他 workflow、自动打包或自动发布
