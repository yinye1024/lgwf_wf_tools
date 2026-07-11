# verify-packaged-skill

## step_slug
`verify-packaged-skill`

## step_name
校验打包产物并执行 authoring audit smoke

## goal
对已落盘的自包含 skill 打包产物执行目录结构、状态边界、manifest、runtime 和 authoring audit smoke 校验，形成可判定通过或失败的结构化验证结果。

## inputs
- 已确认业务流中 `05_verify_packaged_skill` 阶段的目标、`key_nodes` 和向结果汇总阶段交接的产物说明。
- `materialize-packaged-skill` 约定输出的打包产物目录、`materialized_package` 摘要、runner 路径、manifest 路径和步骤文档副本。
- `prepare-packaging-request` 约定输出中与 `audit_smoke` 开关有关的字段语义。
- 计划文档《skill-packaging 工作流创建意图与设计方案》中“验证建议”对结构、manifest、runtime、缓存排除和 smoke fixture 的说明。
- `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md` 与 `.lgwf/create_reference_context/scaffold/scaffold_result_contract.md` 中关于两层拓扑、`wf/docs/steps/`、`ws/.lgwf` 和 `internal_workflow_package` 的约束。
- `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md` 与 `.lgwf/create_reference_context/dsl-assist/create-workflow.md` 中关于 `workflow.lgwf` 布局、相对路径、UTF-8、`lgwf.py audit` 和禁止孙级 workflow 的规则。

## outputs
- 目标 package 内的 `wf/05_verify_packaged_skill/workflow.lgwf`，在单个第一层子 workflow 内编排结构检查、manifest 校验、runtime 校验、audit smoke 和失败诊断汇总。
- `wf/05_verify_packaged_skill/agents/` 中用于解释验证摘要或失败诊断的 prompt 或说明文档。
- `wf/05_verify_packaged_skill/scripts/` 中实现 `validate_output_structure`、`validate_packaging_manifest`、`validate_embedded_runtime`、`run_authoring_audit_smoke` 和 `record_package_validation` 的确定性脚本。
- `wf/05_verify_packaged_skill/resources/` 中保存 manifest 字段说明、结构检查规则、排除目录规则或 smoke fixture 说明。
- 根 `wf/workflow.lgwf` 中对 `05_verify_packaged_skill/workflow.lgwf` 的第五个阶段引用，以及 package 级 `tests/test_scaffold_package_rules.py`、`tests/README.md` 等最小验证入口。
- 该阶段运行时产物约定：`.lgwf/package_validation.json` 和 authoring audit smoke 结果记录。

## dependencies
- 依赖 `materialize-packaged-skill` 已在目标目录落盘，并记录关键生成文件与剩余风险。
- 依赖步骤设计和脚手架约束作为验证基线，不能脱离已确认结构单独发明校验项。
- 验证结果将直接驱动 `summarize-packaging-result` 的通过说明或失败诊断。

## implementation_suggestions
- 把目录存在性、关键文件存在性、相对路径检查、缓存/运行态目录排除和 `workflow.lgwf` 层级检查放在确定性脚本或测试中。
- audit smoke 设计为对打包产物中的 `wf/workflow.lgwf` 执行 authoring audit，不承诺端到端业务成功。
- `tests/test_scaffold_package_rules.py` 至少覆盖根目录无 `workflow.lgwf`、存在 `wf/workflow.lgwf`、每个第一层阶段目录自包含、无孙级 workflow、无根 `SKILL.md`。
- runner 校验必须确认 `scripts/run_local_lgwf_workflow.py` 指向打包产物内的 `vendor/lgwf-client-assist/scripts/lgwf.py`，而不是外部 facade runtime。
- 本阶段只消费结构化执行结果，不直接重新生成打包计划。

## acceptance_notes
- 需要确认 audit smoke 失败后的第一版策略；当前草案只输出失败诊断并阻断成功结论，不增加自动修复链路。
- 需要确认验证阶段必须校验 `wf/docs/steps/*.md` 已复制到打包产物；当前草案把它视为必检项。
- 必须满足 `workflow-audit-checklist.md` 的 verification checklist，尤其是 UTF-8 可读、相对路径可解析、无孙级 workflow 且 `lgwf.py audit` 基本可行。
- 若未来需要把失败诊断自动 handoff 给其他 workflow，应作为新的业务能力重新确认，不在当前步骤内隐式扩展。

## out_of_scope
- 不负责修复 audit 失败。
- 不负责 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成、自动重试或自动回滚。
- 不负责端到端 happy path 成功保证或自动触发 post-fix。

