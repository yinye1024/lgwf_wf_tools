# preflight-packaging-plan

## step_slug
`preflight-packaging-plan`

## step_name
执行前置校验并生成打包计划草案

## goal
在真实写入前校验源 skill 结构、runtime 完整性、目标目录状态和复制排除规则，生成可审阅的 `packaging_plan_proposal`，并把覆盖风险、runner 计划、manifest 计划和 audit smoke 计划显式化。

## inputs
- 已确认业务流中 `02_preflight_packaging_plan` 阶段的目标、`key_nodes`、输出约定和对 `03_confirm_packaging_plan` 的交接说明。
- `prepare-packaging-request` 阶段约定输出的 `packaging_request`、路径上下文和允许写入范围。
- 计划文档《skill-packaging 工作流创建意图与设计方案》中“当前状态”“创建目标”“非目标”“验证建议”对预检范围和最小可用性的说明。
- `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md` 中关于 `wf/` 唯一 workflow root、`ws/.lgwf` 状态边界、`internal_workflow_package` 和 `wf/docs/steps/` 的结构要求。
- `.lgwf/create_reference_context/scaffold/scaffold_result_contract.md` 中 `create_dirs`、`create_files`、`placeholders`、`derived_from_business_flow` 和两层拓扑限制。
- `.lgwf/create_reference_context/dsl-assist/create-workflow.md` 与 `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md` 中关于相对路径、禁止根 `workflow.lgwf`、禁止孙级 workflow 和 `REVIEW`/`APPROVAL` 用法的规则。

## outputs
- 目标 package 内的 `wf/02_preflight_packaging_plan/workflow.lgwf`，在单个第一层子 workflow 内编排源 skill 校验、runtime 校验、目标目录检查和计划草案生成。
- `wf/02_preflight_packaging_plan/agents/` 中用于解释预检结论和计划草案的 prompt 或说明文档。
- `wf/02_preflight_packaging_plan/scripts/` 中实现 `validate_source_skill_structure`、`validate_runtime_source`、`inspect_output_parent_state` 和 `draft_packaging_plan_proposal` 的确定性脚本。
- `wf/02_preflight_packaging_plan/resources/` 中保存排除规则、manifest 必备字段、runner 生成约束或只读模板说明。
- 根 `wf/workflow.lgwf` 中对 `02_preflight_packaging_plan/workflow.lgwf` 的第二个阶段引用。
- 该阶段运行时产物约定：`.lgwf/packaging_preflight.json` 和 `.lgwf/packaging_plan_proposal.json`。

## dependencies
- 依赖 `prepare-packaging-request` 已固化 `packaging_request` 与路径上下文，不能直接从原始意图推导预检字段。
- 下游 `confirm-packaging-plan` 只应消费本阶段生成的 `packaging_plan_proposal`、覆盖风险和待确认上下文。
- 复制排除规则、runner 计划和 manifest 计划必须与现有脚本能力及计划文档描述保持一致，避免在确认前发明未定义的新输出。

## implementation_suggestions
- 将源 skill 必备文件检查、runtime 完整性检查和输出目录状态检查设计为确定性 Python 节点，不把“是否可打包”的事实判断交给 LLM。
- 计划草案可以由脚本先生成结构化对象，再由阶段内 prompt 负责把技术结论整理为可审阅说明；业务对象本身以结构化 JSON 为主。
- `force=true` 且目标目录已存在时，本阶段必须输出明确的覆盖风险结论，交给下一阶段做人审，不在本阶段直接放行。
- 阶段资源路径全部保持 package 内相对路径；目标输出父目录的绝对路径只作为运行时校验输入存在。
- 如需跨阶段复用排除规则或 manifest 字段说明，可放在 `wf/shared/scripts/` 或 `wf/02_preflight_packaging_plan/resources/`，不要把阶段私有 prompt 放入共享目录。

## acceptance_notes
- 需要确认 registry 是否正式从 `tool_workflow` 切换为 `kind=lgwf`；当前草案只要求本阶段在计划中显式列出该待确认项，不在预检阶段自行定案。
- 需要确认是否保留 facade 根 CLI 兼容入口；当前草案要求把这一点作为 `packaging_plan_proposal` 的展示项之一。
- `packaging_plan_proposal` 必须覆盖源 skill 校验结果、runtime 校验结果、目标目录状态、复制排除规则、runner 计划、manifest 计划和 audit smoke 计划，否则下一阶段无法完整确认。
- 本阶段不得真实写入打包产物；任何输出仍应停留在 `.lgwf/` 计划与诊断产物层面。

## out_of_scope
- 不负责人工审批决策落盘。
- 不负责真实复制源 skill 或写入最终 package 产物。
- 不负责 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成、自动修复或端到端运行保证。

