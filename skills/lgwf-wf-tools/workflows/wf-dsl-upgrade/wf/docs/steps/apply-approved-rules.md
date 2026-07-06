# apply-approved-rules

## step_slug
`apply-approved-rules`

## step_name
受控规则应用阶段设计

## goal
设计 `apply_upgrade_rules` 第一层子 workflow，只在 `mode=apply` 且人工批准后，对授权范围内目标文件执行规则化修改，并完整记录写入前校验与实际应用结果。

## inputs
- `build-approved-upgrade-plan` 产出的 `upgrade_plan.json`。
- `prepare-upgrade-plan-approval` 产出的审批决策与授权边界。
- `prepare-target-manifest` 产出的 `target_manifest.json`，用于约束允许写入的目标文件。
- `.lgwf/business_flow.json` 中 `apply_upgrade_rules` 阶段的 `objective`、`key_nodes`、`outputs` 和对 `batch_verify` 的 handoff。
- `.lgwf/create_requirements.json` 中“禁止自由形式 agent 自愈、只允许规则化升级”的需求边界。

## outputs
- `wf/06_apply_upgrade_rules/workflow.lgwf` 的阶段设计草案，至少覆盖 `check_mode_is_apply`、`verify_target_hashes`、`apply_rule_actions` 和 `record_applied_changes`。
- `applied_changes.json` 与 `applied_target_manifest.json` 的结构约束，记录每条实际应用规则、目标文件、写入前 hash、写入结果和跳过原因。
- 写入前校验脚本、规则应用脚本和冲突说明资源的占位清单。
- 向 `verify-upgraded-workflows` 交接的结果字段说明，确保复检阶段只处理本轮真实被修改的目标。

## dependencies
- 依赖 `prepare-upgrade-plan-approval` 的批准结果和授权边界；未经批准不得进入本阶段。
- 依赖 `build-approved-upgrade-plan` 的计划项与 `prepare-target-manifest` 的授权目标清单。
- `verify-upgraded-workflows` 必须消费本阶段产出的被修改目标列表和写入结果，不能自行重新扫描。

## implementation_suggestions
- 在 `wf/06_apply_upgrade_rules/scripts/` 中将“hash 校验”和“规则应用”拆成独立职责，先校验后写入。
- 对每个目标文件应用前记录原始 hash、命中规则和授权来源，写入后记录结果状态，便于冲突排查与审计。
- 当计划项因 hash 不匹配、目标缺失或授权不符而跳过时，必须写入结构化 skip 原因，而不是静默失败。
- 所有写入必须限定在 manifest 授权的目标文件集合内，不允许整包覆盖或自由编辑。

## acceptance_notes
- 必须确认本阶段只有 `mode=apply` 且人工 `approve` 后才会执行真实写入。
- 必须说明写入前 hash 校验如何阻止计划生成后发生的外部漂移。
- 必须保证 `applied_changes.json` 能明确区分“已修改”“跳过”和“失败”三类结果，供后续复检和报告直接消费。

## out_of_scope
- 新增自由形式修复策略。
- 越权修改 manifest 之外的文件。
- 业务流程运行验证。
- 端到端成功保证。
