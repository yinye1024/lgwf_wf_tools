# execute-package-build

## step_slug
`execute-package-build`

## step_name
按确认计划执行确定性打包落盘

## goal
在已批准的 packaging plan 和明确覆盖许可范围内，通过稳定脚本执行目录复制、runtime 内置、runner/manifest 生成与目标目录落盘，产出可继续校验的自包含 skill 初稿。

## inputs
- 已确认的 packaging plan、覆盖许可和路径上下文。
- 已确认业务流中的 `package_execution` 阶段定义和 `copy_skill_files_with_exclusions`、`embed_vendor_runtime`、`generate_runner_and_manifest`、`materialize_packaged_skill` 节点职责。
- `scaffold_plan.target_package_root`、`create_dirs`、`create_files`、`package_profile=internal_workflow_package`。
- `scaffold_template_spec.md` 对根目录、`wf/` 唯一 workflow root、`ws/` 工作目录和共享脚本位置的要求。
- `create-workflow.md` 对 `wf/workflow.lgwf` 薄编排、第一层子 workflow 自包含和相对路径引用的规则。

## outputs
- 目标 package 内的 `wf/07_confirm_step_designs/workflow.lgwf`，承载步骤确认后的实现与落盘编排。
- 目标 package 内的 `wf/07_confirm_step_designs/scripts/prepare_step_design_confirmation.py`、`prepare_step_design_revision_confirmation.py`、`apply_confirmed_step_designs.py`，以及实现执行相关脚本位。
- 目标 package 根目录的 `AGENTS.md`、`README.md`、`scripts/`、`tests/`、`ws/`、`wf/` 框架。
- 目标 package 内的 `wf/docs/steps/*.md` 副本，作为目标 package 的自包含设计依据。
- 目标 package 内的 `wf/<stage>/workflow.lgwf`、`agents/`、`scripts/`、`resources/` 初稿文件树，但不生成根目录 `workflow.lgwf` 或根 `SKILL.md`。

## dependencies
- 依赖 `confirm-packaging-plan` 已形成 confirmed packaging plan。
- 依赖 `wf/docs/steps/*.md` 已经被批准，才能作为实现输入复制到目标 package。
- 为 `verify-packaged-skill` 提供已落盘产物、复制记录、runner/manifest 和步骤文档副本。

## implementation_suggestions
- 稳定动作优先落在确定性脚本，不让 Agent 直接承担复制、覆盖、manifest 生成或 runtime 嵌入。
- `wf/07_confirm_step_designs/workflow.lgwf` 可在阶段内先完成步骤确认上下文准备，再进入实际 package 生成节点，保持“设计确认”和“实现落盘”在同一第一层子 workflow 内闭环。
- 复制步骤文档时固定落到 `wf/docs/steps/<step-slug>.md`，保留原文件名，作为目标 package 的长期说明，不写进运行态目录。
- 根 `wf/workflow.lgwf` 只编排 `02/04/07/09` 四个第一层子 workflow；任何复杂实现逻辑都留在 `wf/07_confirm_step_designs/workflow.lgwf` 内。
- 如需跨阶段 Python helper，只放进 `wf/shared/scripts/`；阶段私有 prompt 仍保留在各自 `agents/`。

## acceptance_notes
- 需要确认 `07_confirm_step_designs` 是否同时负责“步骤确认”和“落地实现”；当前草案沿用现有脚手架命名，避免新增未计划阶段。
- 需要确认第一版占位文件允许范围；当前草案允许保留占位 prompt/README，但目录、关键 workflow 文件和脚本位必须齐全。
- 必须确保 `internal_workflow_package` 不生成根 `SKILL.md`，并且运行状态始终写入 `ws/.lgwf`。

## out_of_scope
- 不负责最终 audit 结论。
- 不负责自动修复失败打包结果。
- 不负责下游 `wf-post-fix` 或 `lgwf-wf-tools` 能力接入。
