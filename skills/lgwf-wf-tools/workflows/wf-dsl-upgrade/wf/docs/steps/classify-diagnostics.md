# classify-diagnostics

## step_slug
`classify-diagnostics`

## step_name
诊断分类阶段设计

## goal
设计 `classify_findings` 第一层子 workflow，把批量 audit 结果与升级规则表结合，稳定地归类为 `auto_fixable`、`manual_review` 和 `unsupported`，为后续升级计划建立可信输入。

## inputs
- `execute-batch-audit` 产出的 `batch_audit_result.json`、`batch_audit_stats.json` 和每个目标的标准化 diagnostics。
- `.lgwf/business_flow.json` 中 `classify_findings` 阶段的 `objective`、`key_nodes`、`outputs` 与对 `build_upgrade_plan` 的 handoff。
- `.lgwf/create_requirements.json` 中“第一版只自动处理明确、低风险、可重复的 DSL 迁移”的需求边界。
- `upgrade_profile` 输入语义与对应的迁移规则定义约束。
- `workflow-audit-checklist.md` 与 `create-workflow.md` 中关于结构化结果、资源路径和子 workflow 自包含的约束。

## outputs
- `wf/03_classify_findings/workflow.lgwf` 的阶段设计草案，至少覆盖 `load_migration_rules`、`match_diagnostics_to_rules`、`classify_auto_fixable`、`classify_manual_review` 和 `classify_unsupported`。
- `classified_findings.json` 与 `classification_summary.json` 的结构约束，说明每个诊断项的分类、匹配规则、原因和风险提示。
- 规则加载脚本、分类策略脚本和分类说明资源的占位清单。
- 向 `build-approved-upgrade-plan` 交接的计划输入说明，明确只有 `auto_fixable` 项可以进入计划构建。

## dependencies
- 依赖 `execute-batch-audit` 提供完整且标准化的 diagnostics。
- `build-approved-upgrade-plan` 只能消费本阶段已分类结果，不能重新依据原始 diagnostics 自行判定。
- 本阶段仍无人工确认，分类争议应以结构化字段和原因说明形式保留到计划与报告阶段。

## implementation_suggestions
- 在 `wf/03_classify_findings/scripts/` 中拆分“规则装载”和“规则匹配”职责，便于后续补充更多 `upgrade_profile`。
- 分类结果中同时保留原始 diagnostic 摘要、命中的规则 id 和未命中原因，避免计划阶段丢失上下文。
- 为 `manual_review` 与 `unsupported` 设计清晰原因枚举，减少后续报告阶段的自由发挥。
- 若当前规则覆盖度不足，不要把模糊问题挤进 `auto_fixable`，而应在结果中显式标记为待人工处理。

## acceptance_notes
- 必须确认分类结果严格区分 `auto_fixable`、`manual_review` 和 `unsupported`，且未知问题不能进入自动修改链路。
- 必须说明规则表按 `upgrade_profile` 装载，第一版至少支持 `latest`，但不承诺覆盖全部 DSL 变化。
- 必须保证输出既可供计划阶段消费，也能在最终报告中直接解释“为什么未自动处理”。

## out_of_scope
- 生成具体升级计划。
- 对目标文件执行修改。
- 自动补齐规则缺口。
- 端到端运行验证。
