# prepare-package-layout

## step_slug
`prepare-package-layout`

## step_name
包结构与根编排设计

## goal
把 `wf-audit-fix` 的目标 package 布局、根 `wf/workflow.lgwf` 薄编排方式、第一层子 workflow 映射和根目录文件边界一次性固定下来，确保后续各阶段实现都遵循同一套两层 workflow 结构。

## inputs
- `.lgwf/create_requirements.json` 中已确认的 `workflow_name=wf-audit-fix`、`target_package_root=skills/wf-audit-fix` 与输入输出边界。
- `.lgwf/business_flow.json` 中已确认的五段业务阶段、`stage_dependencies` 和 `downstream_step_inputs`。
- `04_confirm_business_flow/resources/scaffold_template_spec.md` 中关于 `wf/` 唯一 workflow root、两层 workflow 拓扑、`ws/.lgwf` 状态边界和 `package_profile` 的规范。
- `04_confirm_business_flow/resources/scaffold_result_contract.md` 中 `scaffold_plan` 需要包含的 `create_dirs`、`create_files`、`placeholders` 和 `derived_from_business_flow` 契约。
- `.lgwf/create_reference_context/dsl-assist/create-workflow.md` 与 `workflow-audit-checklist.md` 中关于根 workflow 只做阶段编排、子 workflow 自包含、相对路径和 audit 约束的规则。
- 模板默认 `package_profile=internal_workflow_package`；若后续确认改为 `skill_wrapped_workflow`，只能影响根 `SKILL.md` 是否生成，不改变 `wf/` 作为唯一 workflow root。

## outputs
- 目标 package 的目录与文件清单草案，至少覆盖根 `AGENTS.md`、根 `README.md`、`scripts/`、`tests/`、`ws/`、`wf/`、`wf/shared/scripts/`、`wf/docs/steps/`。
- 根 `wf/workflow.lgwf` 的阶段编排方案，只通过 `STEP ... WORKFLOW` 串联 `wf/02_confirm_requirements/`、`wf/04_confirm_business_flow/`、`wf/07_confirm_step_designs/`、`wf/09_summarize_create_result/`。
- `scaffold_plan` 关键字段如何落到实现阶段的说明，至少覆盖 `create_dirs`、`create_files`、`placeholders` 和 `rules.state_boundary`。
- 文档与最小验证入口的占位规划，例如 `tests/test_scaffold_package_rules.py`、`tests/README.md` 和根文档的职责分工。

## dependencies
- 依赖已确认需求和业务流转，不依赖其他步骤先落地实现文件。
- 该步骤为所有后续阶段提供统一结构护栏；后续步骤不得再发明新的根目录拓扑或新增孙级 workflow。
- 若后续确认 `package_profile` 发生变化，只允许调整根 `SKILL.md` 是否存在，不允许改动阶段目录与根编排边界。

## implementation_suggestions
- 在目标 package 内预留模板要求的全部目录，但只允许 `workflow.lgwf` 出现在 `wf/workflow.lgwf` 与 `wf/<stage>/workflow.lgwf`。
- 根 `wf/workflow.lgwf` 只保留阶段顺序和 route，不展开具体 audit、修复、promote 或 summary 节点实现。
- 将跨阶段 Python helper 放在 `wf/shared/scripts/`，阶段私有 prompt、脚本和资源留在各自 `wf/<stage>/` 目录内。
- 根文档默认按 `internal_workflow_package` 设计：生成 `AGENTS.md` 与 `README.md`，不生成根 `SKILL.md`。

## acceptance_notes
- 必须明确 `wf/` 是唯一 workflow package root，目标 package 根目录永远禁止生成可运行 `workflow.lgwf`。
- 必须把四个第一层子 workflow 与业务流五段需求对应起来，其中“结果汇总与停止”可与 promote 后复检共同落在 `wf/09_summarize_create_result/`，但不得再拆孙级 workflow。
- 必须说明 `ws/` 只是运行目录，运行状态只写入 `ws/.lgwf`，不会回写源码树 `.lgwf`。
- 若审阅者希望新增 facade 接入说明，也只能作为根文档和测试占位内容，不改变 `wf/` 内部拓扑。

## out_of_scope
- `lgwf-wf-prompt-fix` 集成。
- `lgwf-wf-tools` 自动注册或自动发布。
- 自动修复、自动重试和端到端运行保证。
- 直接产出完整 `workflow.lgwf` 实现内容。
