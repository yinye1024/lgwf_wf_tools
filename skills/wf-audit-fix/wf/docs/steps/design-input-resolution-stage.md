# design-input-resolution-stage

## step_slug
`design-input-resolution-stage`

## step_name
输入归一化与范围护栏阶段设计

## goal
为 `input_resolution` 阶段设计第一层子 workflow，负责把 `target_workflow_lgwf`、`max_attempts` 和修复范围限制转换成确定性的目标 package 解析结果、candidate 工作目录规划与后续循环复用的运行上下文。

## inputs
- `.lgwf/create_requirements.json` 中已确认的输入语义：`target_workflow_lgwf`、可选 `max_attempts` 默认值 5，以及“只修复静态 DSL 或 audit 问题”的范围约束。
- `.lgwf/business_flow.json` 中 `input_resolution` 阶段的 `objective`、`key_nodes`、`outputs` 和到 `real_audit_gate` 的 handoff。
- `04_confirm_business_flow/resources/scaffold_template_spec.md` 中关于相对路径、`wf/` 唯一入口、`ws/.lgwf` 状态边界的要求。
- `.lgwf/create_reference_context/dsl-assist/create-workflow.md` 中关于子 workflow 自包含、路径禁止使用绝对路径和 `..` 的规则。
- `prepare-package-layout` 输出的阶段目录映射，尤其是本阶段落在 `wf/02_confirm_requirements/` 的约定。

## outputs
- `wf/02_confirm_requirements/workflow.lgwf` 的设计草案，包含 `load_inputs`、`validate_target_workflow_path`、`resolve_attempt_policy`、`derive_candidate_workspace_plan` 等节点的职责分工。
- 本阶段需要的 `agents/*.md`、`scripts/*.py`、`resources/*.md` 占位清单，用于输入解析、路径规范化、确认上下文和范围说明。
- 结构化阶段输出契约，至少覆盖 `normalized_target_workflow_lgwf`、`resolved_target_package_root`、`attempt_policy`、`candidate_workspace_plan`、`runtime_context`。
- 对下游 `real_audit_gate` 的交接说明，明确哪些字段必须稳定存在。

## dependencies
- 依赖 `prepare-package-layout` 提供的总体拓扑与目录边界。
- 本阶段完成后，`design-audit-gate-stage`、`design-candidate-repair-loop` 和 `design-promote-and-verify-stage` 才能消费一致的路径与循环策略对象。
- 该阶段内部不新增面向目标 workflow 运行时业务的人工确认；当前 workflow 的人工确认边界只发生在 `wf-create` 创建流程本身。

## implementation_suggestions
- 把本阶段内部节点收敛在 `wf/02_confirm_requirements/workflow.lgwf`，不要在根 workflow 中展开细节。
- 使用脚本节点完成路径规范化、目标 package 根推导、candidate 目录命名建议和尝试次数边界校验。
- 若需要面向人工阅读的范围说明，放在 `wf/02_confirm_requirements/resources/`，并与脚本输出的结构化字段保持同名可追踪。
- 输出对象中的所有路径都应以目标 package 内相对路径或受控的运行态路径描述，避免后续步骤依赖 `work_dir` 上跳猜测仓库根。

## acceptance_notes
- 必须明确本阶段只建立静态修复范围和运行上下文，不执行 `lgwf.py audit`、不运行目标 workflow、也不处理目标 workflow 自身 approval。
- 必须说明 candidate 工作目录是为后续隔离修复准备的运行态位置，不能被误解为目标 package 源码目录。
- 若 `scaffold_plan` 文件在实现时尚未单独落盘，也要按模板默认 `internal_workflow_package` 约束设计本阶段输出边界。

## out_of_scope
- `lgwf-wf-prompt-fix` 集成。
- 自动修复逻辑本身。
- 对真实目标目录的任何写操作。
- 端到端业务运行验证。
