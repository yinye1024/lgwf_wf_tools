# render-upgrade-summary

## step_slug
`render-upgrade-summary`

## step_name
升级结果汇总阶段设计

## goal
设计 `summarize_upgrade_result` 第一层子 workflow，把范围收集、审计、分类、计划、审批、应用和复检产物合并成最终 `result_summary.json` 与中文报告，清楚说明处理范围、决策结果、残留问题和后续建议。

## inputs
- `prepare-target-manifest` 产出的目标清单与范围校验结果。
- `execute-batch-audit` 产出的 audit 结果与统计。
- `classify-diagnostics` 产出的分类结果与摘要。
- `build-approved-upgrade-plan` 产出的升级计划与计划摘要。
- `prepare-upgrade-plan-approval` 产出的审批决策与 mode 信息。
- `apply-approved-rules` 产出的实际应用结果。
- `verify-upgraded-workflows` 产出的升级后复检结果与差异摘要。
- `.lgwf/create_requirements.json` 中最终输出应包括中文报告与后续人工建议的需求边界。

## outputs
- `wf/08_summarize_upgrade_result/workflow.lgwf` 的阶段设计草案，至少覆盖 `merge_execution_artifacts`、`summarize_dry_run_or_apply_path`、`highlight_manual_followups` 和 `render_upgrade_report`。
- `result_summary.json` 与 `ws/reports/wf_dsl_upgrade_report.md` 的结构约束，覆盖处理范围、执行路径、修改结果、残留问题和后续人工动作建议。
- 汇总脚本、报告模板和报告片段资源的占位清单。
- 对最终报告如何区分 dry_run、apply、reject 和空计划场景的说明。

## dependencies
- 依赖前七个步骤的结构化产物；任何缺失都应以可解释的空值或状态说明暴露，而不是静默忽略。
- 本阶段是根 workflow 的收尾阶段，结束后不再进入新的自动修改分支。
- 最终报告需要复用前面阶段已经确认的术语和字段，避免总结口径漂移。

## implementation_suggestions
- 在 `wf/08_summarize_upgrade_result/scripts/` 中把“结构化汇总”和“Markdown 报告渲染”拆开，减少格式逻辑与统计逻辑耦合。
- 报告正文默认使用中文，重点说明扫描范围、分类数量、计划项数量、apply 结果、残留问题和建议的人工后续动作。
- 对 dry_run、reject、空计划和部分失败场景都设计明确摘要分支，避免只覆盖成功路径。
- 保留对 `manual_review` 和 `unsupported` 的集中说明，帮助用户后续决定是否新增规则或改走人工修复。

## acceptance_notes
- 必须确认最终输出同时包含机器可读的 `result_summary.json` 和面向人的中文报告。
- 必须说明报告如何引用审批决策与复检结果，避免把 dry_run 误写成已完成修改。
- 必须确保总结阶段不触发新的写入逻辑，只负责归并与呈现已有产物。

## out_of_scope
- 自动启动下游 workflow。
- 自动发布或 registry 接入。
- 端到端业务运行保证。
- 对残留问题执行二次修复。
