# prepare-packaging-request

## step_slug
`prepare-packaging-request`

## step_name
规范化打包请求并冻结路径边界

## goal
把 `packaging_request` 归一化成稳定 JSON，解析 `source_skill`、`output_parent`、`runtime_source`、`force` 和 `audit_smoke`，并在任何真实写入前固定允许写入范围、相对路径规则和后续阶段要消费的请求快照。

## inputs
- 已确认业务流中 `01_prepare_packaging_request` 阶段的目标、`key_nodes` 和输出约定。
- 计划文档《skill-packaging 工作流创建意图与设计方案》中“输入契约建议”“状态与产物建议”“风险与待确认点”对 `packaging_request` 字段语义和默认值的说明。
- `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md` 中关于 `internal_workflow_package`、`wf/` 唯一 workflow root、`ws/.lgwf` 状态边界和相对路径限制的要求。
- `.lgwf/create_reference_context/scaffold/scaffold_result_contract.md` 中 `target_package_root`、`package_profile`、`rules.path_policy` 和 `rules.state_boundary` 的契约。
- `.lgwf/create_reference_context/dsl-assist/create-workflow.md` 与 `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md` 中“根 workflow 只做薄编排、阶段细节下沉到第一层子 workflow、禁止绝对路径与 `..`”的规则。
- `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md` 中关于子 workflow 自包含、状态不穿透和控制面/执行面分离的约束。

## outputs
- 目标 package 内的 `wf/01_prepare_packaging_request/workflow.lgwf`，在单个第一层子 workflow 内编排 `normalize_packaging_request`、`resolve_runtime_source` 和 `freeze_write_scope`。
- `wf/01_prepare_packaging_request/agents/` 中与请求整理和输入解释相关的 prompt 或说明文档；即使阶段最终以脚本为主，也保留阶段说明文件以满足自包含目录契约。
- `wf/01_prepare_packaging_request/scripts/` 中实现请求归一化、路径验证、运行时默认值补全和请求快照落盘的确定性脚本。
- `wf/01_prepare_packaging_request/resources/` 中只读 schema、字段说明或示例输入，用于约束 `packaging_request` 结构和覆盖策略说明。
- 根 `wf/workflow.lgwf` 中对 `01_prepare_packaging_request/workflow.lgwf` 的首个 `STEP ... WORKFLOW` 引用，不在 package 根目录生成 `workflow.lgwf`。
- 该阶段运行时产物约定：`.lgwf/packaging_request.json`、路径上下文快照和允许写入范围说明。

## dependencies
- 作为首个业务阶段，无上游阶段依赖，但必须遵守 `package_profile=internal_workflow_package`、不生成根 `SKILL.md` 和不向目标 package 根目录写 `.lgwf` 的脚手架边界。
- 下游 `preflight-packaging-plan` 只能消费本阶段固化的 `packaging_request` 与路径上下文，不得重复从自然语言输入反向猜测字段。
- 若后续允许 `output_parent` 接受绝对路径，该值只能作为运行时输入保留，不能写回 authoring 资源路径或 `target_package_root`。

## implementation_suggestions
- 将字段默认值、路径标准化、写入范围冻结和 runtime source 解析放在确定性 Python 脚本中，不让 Codex prompt 直接做目录探测或副作用写入。
- `wf/01_prepare_packaging_request/workflow.lgwf` 保持阶段内闭环：先规范化请求，再补齐 runtime source 和写入边界，最后输出供预检使用的请求快照。
- 所有 authoring 资源路径使用 package 内相对路径；运行时绝对路径只能存在于 `.lgwf/packaging_request.json` 或内存 state 中。
- 根 `wf/workflow.lgwf` 只串联阶段，不展开 `normalize_packaging_request` 等内部节点。
- 如需共享稳定技术逻辑，可放入 `wf/shared/scripts/`；但本阶段特有的输入解释、字段语义和风险说明仍留在 `wf/01_prepare_packaging_request/` 下。

## acceptance_notes
- 需要确认是否保留 facade 根 `scripts/package_lgwf_skill.py` 作为兼容入口；当前草案只要求本阶段输出可供 workflow 内部消费的标准请求对象，不绑定最终兼容策略。
- 需要确认 `source_skill` 是否同时支持 workspace 相对路径和用户给定绝对路径；当前草案允许两者作为运行时输入，但不允许把绝对路径写回 authoring 文件。
- 本阶段设计必须可支撑后续 `preflight-packaging-plan` 生成 `packaging_plan_proposal`，因此 `force`、`audit_smoke` 和 `runtime_source` 字段不能省略语义。
- `workflow.lgwf` 只能出现在 `wf/workflow.lgwf` 与 `wf/01_prepare_packaging_request/workflow.lgwf`，不得为单一脚本节点额外制造孙级 workflow。

## out_of_scope
- 不负责真实复制源 skill、嵌入 runtime、生成 runner 或写 `PACKAGING_MANIFEST.json`。
- 不负责 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成、自动修复或自动重试。
- 不负责打包结果的端到端业务成功保证。

