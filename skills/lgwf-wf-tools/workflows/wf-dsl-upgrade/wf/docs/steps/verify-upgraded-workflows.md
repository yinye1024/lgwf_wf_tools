# verify-upgraded-workflows

## step_slug
`verify-upgraded-workflows`

## step_name
升级后复检阶段设计

## goal
设计 `batch_verify` 第一层子 workflow，对本轮真实修改过的 workflow 再次执行静态 audit，比较升级前后结果并产出残留问题摘要。

## inputs
- `apply-approved-rules` 产出的 `applied_changes.json` 与被修改目标列表。
- `execute-batch-audit` 阶段保留的升级前 audit 基线结果。
- `.lgwf/business_flow.json` 中 `batch_verify` 阶段的 `objective`、`key_nodes`、`outputs` 和对 `summarize_upgrade_result` 的 handoff。
- `.lgwf/create_requirements.json` 中“只复检静态兼容性，不运行业务流程”的边界。
- `workflow-audit-checklist.md` 中关于 audit 与结构化 review 输出的约束。

## outputs
- `wf/07_batch_verify/workflow.lgwf` 的阶段设计草案，至少覆盖 `select_modified_targets`、`rerun_audit_for_modified_targets`、`compare_pre_post_audit` 和 `summarize_remaining_findings`。
- `post_upgrade_audit_result.json` 与 `post_upgrade_diff_summary.json` 的结构约束，说明升级后状态、残留 diagnostics 和前后对比摘要。
- 复检脚本、差异对比脚本和结果说明资源的占位清单。
- 交给 `render-upgrade-summary` 的结果字段说明，明确哪些问题已消除、哪些仍需人工处理。

## dependencies
- 依赖 `apply-approved-rules` 提供真实被修改目标列表；若无修改目标，应输出空复检结果而不是重新扫描全量目标。
- 依赖升级前 audit 基线，保证差异比较有据可依。
- `render-upgrade-summary` 直接消费本阶段产出的复检结果与差异摘要。

## implementation_suggestions
- 仅对 `applied_changes.json` 中状态为已修改的目标重新执行 audit，避免无意义的全量复检。
- 将“重新 audit”和“前后对比”分成独立脚本或节点，便于后续单独调试。
- 对仍有残留 diagnostics 的目标保留结构化问题清单和建议后续动作，不把语义判断塞进脚本错误信息。
- 如果本轮为 dry_run 或全部跳过写入，应通过明确状态说明为何没有复检对象。

## acceptance_notes
- 必须确认本阶段不运行业务 workflow，只做升级后静态 audit。
- 必须说明复检对象来源于实际写入结果，而不是原始 target manifest 全量集合。
- 必须保证 `post_upgrade_diff_summary.json` 足够支持最终中文报告直接引用前后变化。

## out_of_scope
- 重新生成升级计划。
- 再次自动修复残留问题。
- 业务级端到端验证。
- 自动批准后续动作。
