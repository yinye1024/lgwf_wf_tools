# summarize-packaging-result

## step_slug
`summarize-packaging-result`

## step_name
汇总打包结果并输出后续建议

## goal
汇总确认计划、打包执行结果和验证结论，输出面向维护者的总结报告、最终产物路径说明、失败原因和后续建议，但不自动触发任何下游 workflow。

## inputs
- 已确认业务流中 `06_summarize_packaging_result` 阶段的目标、`key_nodes` 和最终产物说明。
- `confirm-packaging-plan` 约定输出的 `confirmed_packaging_plan`。
- `materialize-packaged-skill` 约定输出的执行摘要、关键生成文件和剩余风险。
- `verify-packaged-skill` 约定输出的结构化验证结果、authoring audit smoke 结论和失败诊断。
- 计划文档《skill-packaging 工作流创建意图与设计方案》中“创建目标”“非目标”“验证建议”“风险与待确认点”对结果报告边界的说明。
- `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md` 与 `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md` 中关于 `wf/workflow.lgwf`、`ws/.lgwf`、根 `SKILL.md` 和模块边界的规则。

## outputs
- 目标 package 内的 `wf/06_summarize_packaging_result/workflow.lgwf`，在单个第一层子 workflow 内编排结果汇总、报告生成和后续建议暴露。
- `wf/06_summarize_packaging_result/agents/` 中用于解释汇总摘要或 handoff 建议的 prompt 或说明文档。
- `wf/06_summarize_packaging_result/scripts/` 中实现 `summarize_packaging_result`、`emit_packaging_result_report` 和最终摘要固化的确定性脚本。
- `wf/06_summarize_packaging_result/resources/` 中保存报告模板、后续建议模板或只读示例。
- 根 `wf/workflow.lgwf` 中对 `06_summarize_packaging_result/workflow.lgwf` 的第六个阶段引用，以及与之保持一致的根 `README.md`、`AGENTS.md`、`entry_contract.json` 和 `wf/artifact_contracts.json` 内容。
- 该阶段运行时产物约定：`.lgwf/packaging_result_summary.json` 和 `reports/skill-packaging/packaging_result_report.md`。

## dependencies
- 依赖 `verify-packaged-skill` 已产出最终验证摘要。
- 依赖前面各步骤都把生成范围、验证结论和剩余风险记录为结构化对象，避免总结阶段重新读取大量源码。
- 若后续需要 handoff 到其他 workflow，只能暴露建议或 payload，不自动启动下游。

## implementation_suggestions
- `wf/06_summarize_packaging_result/workflow.lgwf` 保持轻量，主要负责汇总输入、调用总结脚本并暴露下一步建议。
- `summarize_packaging_result.py` 以结构化 JSON 为主输入，输出报告摘要、验证状态、remaining risks 和人工后续建议。
- 根 `README.md`、`AGENTS.md`、`entry_contract.json` 与 `wf/artifact_contracts.json` 的说明应与总结结果保持一致，明确 `wf/workflow.lgwf` 是唯一入口，`ws/` 是唯一工作目录。
- 后续动作只写成建议或 handoff payload，不要在本阶段自动触发 `lgwf-wf-tools` 或其他治理链路。

## acceptance_notes
- 结果报告必须包含失败时的人工处理建议；当前草案将其视为必要项。
- 根 `README.md` 与 `AGENTS.md` 可以由实现阶段先建框架，再由本阶段补齐最终运行入口、边界说明和最小验证指引。
- 必须明确当前 workflow 不承诺自动修复、自动重试和端到端成功保证。
- 本阶段结束时只能给出建议或 handoff 输入，不自动启动任何下游 workflow。

## out_of_scope
- 不负责真正执行 post-fix。
- 不负责修改 facade registry、发布流程或安装逻辑。
- 不负责 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成、自动修复或新增业务需求。
