# verify-packaged-skill

## step_slug
`verify-packaged-skill`

## step_name
校验打包产物并执行 audit smoke

## goal
对已落盘的自包含 skill 初稿执行目录结构、状态边界、runtime 完整性和 audit smoke 校验，形成可判定通过或失败的结构化验证结果。

## inputs
- `execute-package-build` 产出的目标 package 目录、复制记录、runner/manifest 与步骤文档副本。
- 已确认业务流中的 `package_verification` 阶段定义和 `validate_packaged_layout`、`validate_runtime_is_embedded`、`run_audit_smoke`、`summarize_verification_findings` 节点职责。
- `scaffold_plan.create_dirs`、`create_files`、`placeholders`，用于对照最小存在性检查。
- `workflow-audit-checklist.md` 中的结构、resource refs、`workflow.lgwf` 布局、相对路径和 verification 要求。
- `create-workflow.md` 中关于 `scripts/lgwf.py audit <package-root>\\workflow.lgwf` 的 authoring audit 规则。

## outputs
- 目标 package 内的 `wf/09_summarize_create_result/workflow.lgwf` 中对验证结果的汇总入口，或等价的验证阶段编排。
- 目标 package 内的 `wf/09_summarize_create_result/scripts/` 中用于汇总验证结论的脚本位。
- 目标 package 内最小验证入口 `tests/test_scaffold_package_rules.py` 与 `tests/README.md` 的实现方向。
- 结构化验证结果对象设计，供结果汇总阶段消费。

## dependencies
- 依赖 `execute-package-build` 已在目标目录落盘。
- 依赖 `create_dirs/create_files` 作为验证基线，不能脱离脚手架计划单独发明校验项。
- 验证结果将直接驱动 `summarize-packaging-result` 的通过说明或失败诊断。

## implementation_suggestions
- 把目录存在性、关键文件存在性、相对路径检查和 `workflow.lgwf` 层级检查放在确定性脚本或测试中。
- audit smoke 设计为对目标 package 的 `wf/workflow.lgwf` 进行 authoring audit，不要求在本阶段承诺端到端业务成功。
- `tests/test_scaffold_package_rules.py` 至少覆盖根目录无 `workflow.lgwf`、存在 `wf/workflow.lgwf`、每个第一层阶段目录自包含、无孙级 workflow、无根 `SKILL.md`。
- 汇总节点只消费结构化验证结果，不直接重新推导打包计划。

## acceptance_notes
- 需要确认 audit smoke 失败后的第一版策略；当前草案只输出失败诊断，不增加自动修复链路。
- 需要确认验证阶段是否应校验 `wf/docs/steps/*.md` 已复制到目标 package；当前草案认为这是必检项。
- 必须满足 `workflow-audit-checklist.md` 的 verification checklist，尤其是 UTF-8 可读、相对路径可解析和 `compile/audit` 基本可行。

## out_of_scope
- 不负责修复 audit 失败。
- 不负责端到端 happy path 成功保证。
- 不负责自动重试、自动回滚或 post-fix 触发。
