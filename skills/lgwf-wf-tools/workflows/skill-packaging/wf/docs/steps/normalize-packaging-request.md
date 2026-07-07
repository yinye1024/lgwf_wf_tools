# normalize-packaging-request

## step_slug
`normalize-packaging-request`

## step_name
规范化打包请求并固化路径上下文

## goal
把用户自然语言请求、源 Codex skill 路径、目标输出目录线索和覆盖策略整理成稳定的结构化 packaging request，为后续前置校验和计划生成提供唯一输入对象。

## inputs
- 已确认需求中的 `target_package_root`、覆盖策略、运行边界和禁止事项。
- 已确认业务流中的 `request_intake` 阶段定义、`normalize_packaging_request`、`resolve_source_skill_path`、`collect_packaging_constraints` 节点职责。
- `scaffold_plan.target_package_root`、`package_profile=internal_workflow_package`、`rules.path_policy`、`rules.state_boundary`。
- `scaffold_template_spec.md` 中关于相对路径、`wf/` 唯一 workflow root、`ws/.lgwf` 状态边界的要求。
- `create-workflow.md` 中“根 workflow 只做薄编排、阶段细节落到第一层子 workflow”的规则。

## outputs
- 目标 package 内的 `wf/02_confirm_requirements/workflow.lgwf`，承载请求整理、路径解析和需求确认闭环。
- 目标 package 内的 `wf/02_confirm_requirements/agents/`，放置请求整理与需求 proposal/确认相关 prompt。
- 目标 package 内的 `wf/02_confirm_requirements/scripts/finish_raw_intent.py`，负责把自然语言入口整理为结构化 request。
- 目标 package 内的 `wf/02_confirm_requirements/scripts/prepare_requirements_confirmation.py`、`prepare_requirements_revision_confirmation.py`、`apply_confirmed_requirements.py`。
- 根 `wf/workflow.lgwf` 中对 `02_confirm_requirements/workflow.lgwf` 的第一层 `STEP ... WORKFLOW` 引用，不在根目录生成 `workflow.lgwf`。

## dependencies
- 无前置步骤，但实现时依赖根 `wf/workflow.lgwf` 的阶段编排约定。
- 依赖 `confirm_requirements` 人工确认边界，不能把未确认需求直接传给后续阶段。
- 依赖 `scaffold_plan.create_files` 中已约定的 `wf/02_confirm_requirements/scripts/*` 文件位。

## implementation_suggestions
- 在 `wf/02_confirm_requirements/workflow.lgwf` 内把请求整理、需求 proposal、需求确认和确认结果固化放进同一个第一层子 workflow，不再拆孙级 workflow。
- 使用 `CODEX` 节点生成需求 proposal，使用 `REVIEW` 或既定确认节点表达 `approve/reject` 或修订闭环，保持阶段内部自洽。
- 把路径标准化、覆盖策略归一化和源 skill 路径解析放进 `scripts/finish_raw_intent.py` 或同阶段 Python 节点，不让 Agent 直接做目录探测和副作用写入。
- 所有资源路径都使用目标 package 内相对路径；任何 workspace 绝对路径仅能出现在运行时输入对象，不得写入 authoring 文件。
- 根 `wf/workflow.lgwf` 只串联阶段，不展开本阶段内部节点。

## acceptance_notes
- 需要确认 `02_confirm_requirements` 是否同时承载自然语言入口整理与需求确认；当前草案按脚手架文件清单采用单阶段聚合设计。
- 需要确认源 skill 路径解析失败时是直接 `FAIL_ALL` 还是先回到修订确认；当前草案保留为阶段内控制流，不外泄给父 workflow。
- 必须满足 `workflow-audit-checklist.md`：`workflow.lgwf` 只出现在 `wf/workflow.lgwf` 和 `wf/<stage>/workflow.lgwf` 两类位置。

## out_of_scope
- 不负责实际复制源 skill、嵌入 runtime、生成 manifest。
- 不负责 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成。
- 不负责自动修复、自动重试或端到端运行保证。
