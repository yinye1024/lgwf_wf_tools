# confirm-packaging-plan

## step_slug
`confirm-packaging-plan`

## step_name
展示打包计划并完成人工确认

## goal
把前置校验得到的 packaging plan proposal、覆盖风险、兼容入口选择和失败处理边界整理成明确可审阅的确认上下文，由人工决定继续或终止。

## inputs
- `build-preflight-plan` 输出的 packaging plan proposal、风险结论和待确认上下文。
- 已确认业务流中的 `plan_confirmation` 阶段定义和 `prepare_packaging_plan_confirmation`、`confirm_packaging_plan`、`persist_packaging_plan_decision` 节点职责。
- `scaffold_plan.rules.state_boundary`，尤其是“运行状态写入 `ws/.lgwf`、不向目标 package 根目录写入 `.lgwf`”。
- `approval.md` 同类人工展示模板约束，以及 `workflow-audit-checklist.md` 对 `APPROVAL/REVIEW` 的使用限制。

## outputs
- 目标 package 内的 `wf/04_confirm_business_flow/workflow.lgwf` 中确认分支、修订分支或失败终止分支的编排。
- 目标 package 内的 `wf/04_confirm_business_flow/agents/` 中用于计划确认展示的 prompt 或说明文档。
- 目标 package 内的 `wf/04_confirm_business_flow/scripts/prepare_business_flow_confirmation.py`、`prepare_business_flow_revision_confirmation.py`、`apply_confirmed_business_flow.py`，或等价的计划确认脚本位。
- 根 `wf/workflow.lgwf` 保持对本阶段单一子 workflow 的引用，不承接阶段内 `approve/reject/revise` 细节。

## dependencies
- 依赖 `build-preflight-plan` 已生成稳定 proposal 与风险结论。
- `approve` 后才能进入 `execute-package-build`；`reject` 应在子 workflow 内 `FAIL_ALL`。
- 依赖共享确认 IO 能把 proposal、decision 和 confirmed plan 以稳定对象形态交给下游。

## implementation_suggestions
- 阶段内使用 `REVIEW` 表达 `approve/revise/reject` 更合适；如果最终约束只允许二元审批，可退化为 `APPROVAL` 并把修订逻辑收敛到 proposal 生成节点。
- 计划确认展示应明确覆盖风险、兼容入口、失败处理边界和不自动修复范围，避免审批记录替代业务对象本身。
- `apply_confirmed_business_flow.py` 或等价脚本只负责把已确认 proposal 固化为 confirmed artifact，不把人工记录原样当作业务结构。
- 根 workflow 不得感知本阶段的内部 review route，避免父子流程耦合。

## acceptance_notes
- 需要确认本 workflow 第一版最终采用 `REVIEW` 还是 `APPROVAL`。当前草案偏向 `REVIEW`，因为业务风险项存在“修订后再确认”需求。
- 需要确认 `reject` 是否直接终止整个 workflow；当前草案按业务边界采用 `FAIL_ALL`。
- 必须确认已批准对象是 packaging plan/confirmed plan，而不是 human decision record。

## out_of_scope
- 不负责执行真实打包。
- 不负责自动生成修复方案或再次尝试计划。
- 不负责将该 workflow 自动接入 facade 或 registry。
