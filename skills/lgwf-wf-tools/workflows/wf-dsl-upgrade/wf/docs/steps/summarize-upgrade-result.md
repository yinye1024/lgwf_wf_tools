# summarize-upgrade-result

## step_slug
`summarize-upgrade-result`

## step_name
升级结果汇总与报告渲染

## goal
设计 `wf/04_summarize_upgrade_result/workflow.lgwf`，把范围收集、范围审批和 FOREACH 单目标升级结果合并成稳定的 `result_summary.json` 与中文报告，明确本次 run 的最终状态、剩余风险、跳过原因和建议下一步。

## inputs
- 上游阶段或节点：
  - `collect-authorized-targets` 的目标与范围校验结果
  - `confirm-scope` 的范围审批记录
  - `upgrade-one-target` 在 FOREACH 中返回的每目标 audit、修复和最终状态
- 依赖文件或状态：
  - `.lgwf/business_flow.json` 中 `summarize_upgrade_outcome` 阶段定义
  - `docs_tmp/wf-dsl-upgrade-development.md`
- 关键约束：
  - 最终 `status` 必须区分 `dry_run`、`applied`、`skipped`、`failed`、`partial`
  - 报告必须列出剩余风险、未处理目标、跳过原因和建议下一步
  - 即使业务逻辑主要在脚本中，阶段目录仍需保留 `agents/`、`scripts/`、`resources/`

## outputs
- 预期生成的文件：
  - `wf/04_summarize_upgrade_result/workflow.lgwf`
  - `wf/04_summarize_upgrade_result/scripts/*.py`
  - `wf/04_summarize_upgrade_result/resources/*`
  - `ws/.lgwf/result_summary.json`
  - `ws/reports/wf-dsl-upgrade/report.md`
- 预期生成的目录：
  - `wf/04_summarize_upgrade_result/agents/`
  - `wf/04_summarize_upgrade_result/scripts/`
  - `wf/04_summarize_upgrade_result/resources/`
- 交付给下游的结构片段：
  - 最终状态、目标范围、审批结论、处理结果和后续建议
  - 面向人的中文报告

## dependencies
- 前置步骤：
  - `define-shared-helper-and-verification`
  - `collect-authorized-targets`
  - `confirm-scope`
  - `upgrade-one-target`
- 依赖节点：
  - `state.wf_dsl_upgrade.target_results`
  - `state.wf_dsl_upgrade`，作为 `exec.run_python INPUT` 的对象输入；不要把 `INPUT` 直接指向列表型 `state.wf_dsl_upgrade.target_results`
- 需要人工确认的位置：
  - 当前阶段不新增人工确认

## implementation_suggestions
- 将“结构化 summary 计算”和“Markdown 报告渲染”拆成独立脚本，减少统计逻辑与排版逻辑耦合。
- 对 `dry_run`、`reject`、FOREACH 空结果、单目标修复成功、部分失败和人工处理分别定义明确状态映射，不继续使用 `draft` 或 `placeholder`。
- 报告正文默认使用中文，统一复用前面阶段的术语，例如 `needs_manual_review`、`dry_run_failed`、`repaired`、`passed`、`remaining_diagnostic_count`。
- 资源目录中可以放报告模板或片段，不要让报告脚本自行硬编码过长正文。

## acceptance_notes
- 重点确认总结阶段只做归并和呈现，不触发新的目标写入。
- 重点确认无论 `apply` 是否发生，都能输出完整 `result_summary.json` 和 `report.md`。
- 重点确认报告不会再出现“占位”“placeholder”“draft”等初稿语气，除非是在测试 fixture 中专门断言旧行为不可接受。

## out_of_scope
- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 自动启动其他 workflow 或自动发布 registry 变更
