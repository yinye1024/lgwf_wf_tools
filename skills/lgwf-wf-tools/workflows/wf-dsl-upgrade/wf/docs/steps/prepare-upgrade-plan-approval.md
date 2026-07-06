# prepare-upgrade-plan-approval

## step_slug
`prepare-upgrade-plan-approval`

## step_name
升级计划确认阶段设计

## goal
设计 `confirm_upgrade_plan` 第一层子 workflow，按共享 approval 模板把扫描范围、分类结果、升级计划和 dry_run/apply 决策展示给用户，形成不可绕过的人审闸门。

## inputs
- `prepare-target-manifest` 产出的 `target_manifest.json` 和范围校验结果。
- `execute-batch-audit` 产出的 `batch_audit_result.json` 与统计摘要。
- `classify-diagnostics` 产出的 `classified_findings.json` 与分类统计。
- `build-approved-upgrade-plan` 产出的 `upgrade_plan.json` 与 `upgrade_plan_summary.json`。
- `.lgwf/create_requirements.json` 中 `mode` 输入语义，以及要求在 apply 前必须人工确认的业务边界。
- 共享 approval 模板约束与 `workflow-audit-checklist.md` 中关于 `APPROVAL`/`REVIEW` 路由的规则。

## outputs
- `wf/05_confirm_upgrade_plan/workflow.lgwf` 的阶段设计草案，至少覆盖 `prepare_approval_context`、`present_scope_and_counts`、`present_rule_impacts` 和 `capture_approval_decision`。
- `upgrade_plan_confirmation_context.json` 与 `upgrade_plan_approval.json` 的结构约束，说明审批展示内容、允许决策与后续 route。
- approval 展示 Markdown、说明资源和必要的上下文整理脚本占位清单。
- 向 `apply-approved-rules` 与 `render-upgrade-summary` 交接的决策字段说明，明确 `approve`、`reject` 以及 dry_run 分支如何控制后续执行。

## dependencies
- 依赖前三个只读阶段和计划构建阶段的全部结构化产物。
- `apply-approved-rules` 只有在 `approve` 且 `mode=apply` 时才能继续；`render-upgrade-summary` 需要消费本阶段决策结果决定总结路径。
- 本阶段是目标 workflow 的核心人工确认点，不能被其他阶段替代或绕过。

## implementation_suggestions
- 在 `wf/05_confirm_upgrade_plan/` 内使用 `REVIEW` 或符合共享模板的确认节点表达 `approve/reject` 决策，并把展示文本、统计摘要与计划详情放在同一阶段内组织。
- 把 approval 上下文构建放到脚本节点，确保展示信息来自固定 JSON 产物，而不是临时拼接自然语言。
- 明确 dry_run 场景即使 `approve` 也不进入真实写入，而是直接将决策与计划一并交给总结阶段。
- 对 `reject` 路径设计清晰终止语义，防止后续 apply 或 verify 误运行。

## acceptance_notes
- 必须确认 approval 上下文展示扫描数量、分类数量、计划项数量、将修改的文件范围、规则影响和 mode 决策信息。
- 必须说明 `approve` 后的授权边界如何被 apply 阶段消费，避免执行阶段扩大范围。
- 必须保证 `reject` 或 dry_run 分支不会触发真实写入。

## out_of_scope
- 修改目标文件本身。
- 升级后复检逻辑。
- facade 级 approval 流程调整。
- 端到端业务 happy path 保证。
