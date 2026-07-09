# confirm-packaging-plan

## step_slug
`confirm-packaging-plan`

## step_name
展示打包计划并完成显式人工确认

## goal
把前置校验得到的 `packaging_plan_proposal`、覆盖风险、兼容入口选择和失败处理边界整理成明确可审阅的确认上下文，并把 `approve` 收紧为真实物化前的写入放行 gate：只有当 `proposal.ready_to_package`、关键 preflight 真值和覆盖风险结论都满足继续条件时，人工才可以给出 `approve`；否则应通过 `revise` 关闭问题或用 `reject` 终止。

## inputs
- 已确认业务流中 `03_confirm_packaging_plan` 阶段的目标、`key_nodes`、人工确认边界和 `approve/revise/reject` 规则。
- `preflight-packaging-plan` 约定输出的 `packaging_plan_proposal`、预检结论、覆盖风险说明和待确认上下文。
- 计划文档《skill-packaging 工作流创建意图与设计方案》中“风险与待确认点”对 registry 切换、兼容 CLI、覆盖风险和 audit smoke 策略的说明。
- `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md` 与 `.lgwf/create_reference_context/scaffold/scaffold_result_contract.md` 中关于 `ws/.lgwf` 状态边界和 `internal_workflow_package` 的约束。
- `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md` 中对 `REVIEW` 固定三选项、`reject -> FAIL_ALL` 和“确认记录不能代替 confirmed 业务对象”的限制。

## outputs
- 目标 package 内的 `wf/03_confirm_packaging_plan/workflow.lgwf`，在单个第一层子 workflow 内编排确认上下文准备、`REVIEW` 决策和 `confirmed_packaging_plan` 固化。
- `wf/03_confirm_packaging_plan/agents/` 中用于计划展示、覆盖风险提示和修订说明的 prompt 或文档。
- `wf/03_confirm_packaging_plan/scripts/` 中实现确认上下文准备、修订重入和 confirmed artifact 固化的脚本。
- `wf/03_confirm_packaging_plan/resources/` 中保存人工确认文案、展示模板补充字段或覆盖风险提示说明。
- 根 `wf/workflow.lgwf` 中对 `03_confirm_packaging_plan/workflow.lgwf` 的第三个阶段引用，不在父 workflow 暴露本阶段内部 route 细节。
- 该阶段运行时产物约定：`.lgwf/packaging_plan_confirmation_context.json`、`.lgwf/packaging_plan_approval.json` 和 `.lgwf/confirmed_packaging_plan.json`。

## dependencies
- 依赖 `preflight-packaging-plan` 已生成稳定 proposal 与风险结论。
- 依赖 `preflight-packaging-plan` 已显式提供 `proposal.ready_to_package`、`proposal.preflight.source_skill.ok`、`proposal.preflight.runtime.ok`、`proposal.preflight.output.target_exists`、`proposal.preflight.output.overwrite_requires_confirmation` 和 `proposal.preflight.output.issues` 等事实字段，供本阶段做真实放行判断。
- 只有 `approve` 后才能进入 `apply_confirmed_packaging_plan -> materialize-packaged-skill`；`approve` 不是展示通过，而是允许生成 `confirmed_packaging_plan` 并继续真实写入。
- `revise` 留在本阶段内部重审；重入时要消费 `latest_revision_request`，把上一轮问题收敛到“已关闭 / 未关闭 / 当前阶段无法关闭”三类，而不是重复审同一 proposal。
- `reject` 应在子 workflow 内 `FAIL_ALL`；当阻塞项属于当前阶段无权修复的客观事实时，不应继续无限 `revise`。
- 依赖确认 IO 把 proposal、decision 和 confirmed plan 以稳定对象形态交给下游，不让 human decision record 充当业务对象。

## implementation_suggestions
- 阶段内优先使用 `REVIEW` 表达固定三选项，不要把 `revise` 强行塞进 `APPROVAL`。
- 确认展示必须明确覆盖风险、兼容入口、失败处理边界和不自动修复范围，避免审批记录替代业务对象本身。
- reviewer 必须把 `proposal.ready_to_package`、`proposal.preflight.source_skill.ok`、`proposal.preflight.runtime.ok`、`proposal.preflight.output.issues` 作为 `approve` 前必查门槛；当 `proposal.preflight.output.target_exists=true` 时，还要结合 `proposal.output.force`、`proposal.risks` 和 `proposal.pending_decisions` 判断覆盖风险是否已被显式接受。
- `revise` 重入时优先核对 `latest_revision_request` 中上一轮 `changes`、`comment` 或 `reason` 是否已关闭；继续 `revise` 时必须指出未关闭项，不能只重复泛化意见。
- 审批记录里的 `changes`、`comment` 和 `reason` 必须能映射到具体 `proposal` section、`proposal.preflight` 字段、风险项或待确认项，便于下一轮确认和人工快速定位。
- 当 `force=true` 且目标目录已存在时，把覆盖风险确认作为本阶段的条件性关键节点留在同一子 workflow 内，不额外拆新阶段。
- 固化脚本只负责从 proposal 生成 `confirmed_packaging_plan`，不把 `decision`、`comment` 等控制面字段原样写入 confirmed 业务对象。
- 父 workflow 只串联本阶段，不承接 `approve/revise/reject` 内部 route，避免父子流程耦合。

## acceptance_notes
- 当前草案要求第一版固定采用 `REVIEW`，因为业务上已明确存在“修订后再确认”和条件性覆盖风险确认需求。
- `approve` 必须被当作真实写入放行，而不是计划展示完整即可通过；如果 `proposal.ready_to_package=false`、关键 preflight 检查失败、`proposal.preflight.output.issues` 非空，或覆盖风险仍未形成明确结论，本阶段只能继续 `revise` 或直接 `reject`。
- `revise` 的目标是关闭上一轮问题，而不是重复复核同一 proposal；当 `latest_revision_request` 暴露的关键项在本阶段无法关闭时，应升级为 `reject`，避免确认阶段空转。
- `reject` 应直接终止整个 workflow；若后续希望保留“退回预检阶段重新生成”的路径，需要回到业务流确认重新定义。
- 必须确认已批准对象是 `packaging_plan_proposal`/`confirmed_packaging_plan`，而不是 `review_result` 或 human decision record。
- 审批记录必须能映射到具体字段或风险项；至少要让后续 reviewer 只看 `.lgwf/packaging_plan_approval.json` 也能快速定位本轮结论依赖的 `proposal` / `proposal.preflight` 证据。
- 阶段说明必须继续强调默认 `auto_human_policy=forbidden`，不把确认节点自动化为无人工审阅的写入放行器。

## out_of_scope
- 不负责执行真实打包。
- 不负责 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成、自动修复或自动重试。
- 不负责将该 workflow 自动接入 facade、registry 或发布流程。
