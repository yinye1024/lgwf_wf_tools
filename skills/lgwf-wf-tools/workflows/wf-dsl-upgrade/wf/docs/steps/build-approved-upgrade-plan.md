# build-approved-upgrade-plan

## step_slug
`build-approved-upgrade-plan`

## step_name
升级计划构建阶段设计

## goal
设计 `build_upgrade_plan` 第一层子 workflow，只为 `auto_fixable` 问题生成受控升级计划，明确目标文件、规则、风险和预期影响，并为后续人工确认提供稳定对象。

## inputs
- `classify-diagnostics` 产出的 `classified_findings.json` 与 `classification_summary.json`。
- `prepare-target-manifest` 产出的 `target_manifest.json`，用于绑定每条计划项的授权范围。
- `.lgwf/business_flow.json` 中 `build_upgrade_plan` 阶段的 `objective`、`key_nodes`、`outputs` 和对 `confirm_upgrade_plan` 的 handoff。
- `.lgwf/create_requirements.json` 中 `mode=dry_run|apply` 与 `upgrade_profile` 的输入约束。
- `scaffold_template_spec.md` 和 `create-workflow.md` 中关于阶段自包含、路径安全和结果文件布局的规则。

## outputs
- `wf/04_build_upgrade_plan/workflow.lgwf` 的阶段设计草案，至少覆盖 `filter_auto_fixable_findings`、`build_plan_items`、`attach_risk_levels` 和 `summarize_plan_scope`。
- `upgrade_plan.json` 与 `upgrade_plan_summary.json` 的结构约束，确保每条 plan item 都包含 `target file`、`rule id`、`risk`、`change summary` 和 `expected impact`。
- 计划构建脚本、风险分级策略和计划说明资源的占位清单。
- 交给 `prepare-upgrade-plan-approval` 的上下文字段说明，包括 dry_run/apply 分支提示、目标文件范围和计划统计。

## dependencies
- 依赖 `classify-diagnostics` 提供稳定的分类结果；若无 `auto_fixable` 项，也需要产出空计划和原因说明。
- 依赖 `prepare-target-manifest` 提供授权边界，所有计划项都必须可追溯到 manifest 中的目标文件。
- `prepare-upgrade-plan-approval` 直接消费本阶段输出，不能再重新组装或自由改写计划项语义。

## implementation_suggestions
- 在 `wf/04_build_upgrade_plan/scripts/` 中单独实现 plan item 构建与风险分级，避免与分类脚本混在一起。
- 计划项建议保留目标 id、目标 package 路径、命中诊断、规则版本和预期副作用说明，便于 approval 与后续 apply 双方复用。
- 对 `dry_run` 与 `apply` 统一使用同一计划结构，只在后续 approval 与执行分支上区分是否真实写入。
- 若某目标命中多个可自动规则，需在计划对象中保持顺序与冲突说明，避免 apply 阶段二次猜测。

## acceptance_notes
- 必须确认升级计划只包含 `auto_fixable` 问题，`manual_review` 与 `unsupported` 只进入摘要和报告，不进入写入计划。
- 必须说明空计划、全失败或部分失败场景如何在 `upgrade_plan_summary.json` 中表达，避免 approval 阶段缺少上下文。
- 必须保证每条计划项都能回溯到具体目标文件、规则 id 和风险等级。

## out_of_scope
- 人工确认展示本身。
- 真实写入目标文件。
- 复检升级结果。
- 自动解决规则冲突之外的语义问题。
