# build-preflight-plan

## step_slug
`build-preflight-plan`

## step_name
执行前置校验并生成打包计划草案

## goal
利用确定性脚本校验源 skill 结构、runtime 依赖、目标目录状态和排除规则，形成可审阅的 packaging plan proposal 与风险结论。

## inputs
- 上一步输出的结构化 packaging request 与路径上下文。
- 已确认业务流中的 `preflight_validation` 阶段定义和 `validate_source_skill_layout`、`validate_runtime_dependencies`、`evaluate_target_directory_state`、`build_packaging_plan` 节点职责。
- `scaffold_plan.create_dirs`、`create_files`、`placeholders`，尤其是 `wf/shared/scripts`、`wf/04_confirm_business_flow/scripts/scaffold_package.py`、`resources/scaffold_*`。
- `scaffold_template_spec.md` 与 `scaffold_result_contract.md` 中关于 `scaffold_plan` 最小字段、`package_profile`、目录层级和状态边界的要求。
- `create-workflow.md` 与 `workflow-audit-checklist.md` 中关于相对路径、禁止根 `workflow.lgwf` 和禁止孙级 workflow 的规则。

## outputs
- 目标 package 内的 `wf/04_confirm_business_flow/workflow.lgwf`，承载前置校验、打包计划生成与后续确认入口。
- 目标 package 内的 `wf/04_confirm_business_flow/scripts/scaffold_package.py`，负责按模板生成确定性 `scaffold_plan`。
- 目标 package 内的 `wf/04_confirm_business_flow/resources/scaffold_package_template.json`、`scaffold_template_spec.md`、`scaffold_result_contract.md`。
- 目标 package 内的 `wf/shared/scripts/confirmation_io.py`，用于跨阶段共享确认输入输出处理。
- 根 `wf/workflow.lgwf` 中对 `04_confirm_business_flow/workflow.lgwf` 的第一层阶段引用。

## dependencies
- 依赖 `normalize-packaging-request` 固化的 packaging request 和路径约束。
- 依赖需求确认结果已经可读，不能从未确认需求直接推导计划。
- 为 `confirm-packaging-plan` 提供 proposal、风险摘要和待确认上下文。

## implementation_suggestions
- 把源 skill 结构校验、runtime 依赖校验、目标目录状态检查和脚手架计划生成都设计为阶段内确定性 Python 节点，不让 Codex 直接决定文件复制策略。
- `scaffold_package.py` 只负责根据已确认需求、业务流和模板产出 `scaffold_plan`，不直接创建最终 package 文件树。
- `wf/04_confirm_business_flow/workflow.lgwf` 内可先 `PY` 生成校验结果，再 `CODEX` 生成业务流/计划解读文本，但计划对象本身以确定性脚本输出为主。
- 资源文件保留在 `wf/04_confirm_business_flow/resources/`，供 audit、实现阶段和人工确认共同引用。
- 如果需要共享确认序列化逻辑，优先放入 `wf/shared/scripts/confirmation_io.py`，不要把阶段私有 prompt 放进共享目录。

## acceptance_notes
- 需要确认 `scripts/package_lgwf_skill.py` 的 CLI 是否继续作为兼容入口暴露；当前草案仅要求在前置校验和计划阶段保留脚本型稳定动作边界。
- 需要确认无覆盖风险场景是否仍必须进入人工确认；当前设计保留计划确认步骤，避免在实现阶段自行放宽约束。
- 必须明确 `scaffold_plan` 至少含有 `workflow_name`、`target_package_root`、`package_profile`、`rules`、`create_dirs`、`create_files`、`placeholders`、`derived_from_business_flow`。

## out_of_scope
- 不负责人工审批决策落盘。
- 不负责真实复制源 skill 或写入最终 package 初稿。
- 不负责自动修复、E2E 运行保证或下游 post-fix 集成。
