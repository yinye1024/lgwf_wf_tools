# summarize-packaging-result

## step_slug
`summarize-packaging-result`

## step_name
整理结果报告并暴露后续动作

## goal
汇总确认计划、打包执行结果和验证结论，输出面向维护者的总结报告、最终产物路径说明和失败时的后续建议。

## inputs
- `confirm-packaging-plan` 的 confirmed packaging plan。
- `execute-package-build` 的执行结果、生成文件清单和占位说明。
- `verify-packaged-skill` 的结构化验证结果、audit smoke 结论和失败诊断。
- 已确认业务流中的 `result_summary` 阶段定义和 `prepare_result_summary`、`write_packaging_report`、`expose_next_actions` 节点职责。
- `scaffold_plan.placeholders` 与 `rules.state_boundary`，用于说明设计边界和未实现范围。

## outputs
- 目标 package 内的 `wf/09_summarize_create_result/workflow.lgwf`，承载汇总与交接逻辑。
- 目标 package 内的 `wf/09_summarize_create_result/scripts/summarize_create_result.py`。
- 面向维护者的结果摘要结构，包括最终产物路径、关键约束、验证结论、占位内容和后续建议。
- 根 `README.md` 与 `AGENTS.md` 中需要承接的运行入口、边界说明和最小验证指引。

## dependencies
- 依赖 `verify-packaged-skill` 已产出最终验证摘要。
- 依赖前面各步骤都把生成范围和占位内容记录为结构化对象，避免总结阶段重新读取大量源码。
- 若后续需要 handoff 到其他 workflow，只能暴露建议，不自动启动下游。

## implementation_suggestions
- `wf/09_summarize_create_result/workflow.lgwf` 保持轻量，主要负责汇总输入、调用总结脚本并暴露下一步建议。
- `summarize_create_result.py` 以结构化 JSON 为主输入，输出报告摘要和清晰的 remaining risks。
- 根 `README.md` 与 `AGENTS.md` 的说明应与总结结果保持一致，明确 `wf/workflow.lgwf` 是唯一入口，`ws/` 是唯一工作目录。
- 后续动作只写成建议或 handoff payload，不要在本阶段自动触发 `wf-post-fix`、`lgwf-wf-tools` 或其他治理链路。

## acceptance_notes
- 需要确认结果报告中是否必须包含失败时的人工处理建议；当前草案认为这是必要项。
- 需要确认根 `README.md` 与 `AGENTS.md` 是在本步骤生成还是由执行步骤预建、汇总步骤补全；当前草案允许执行步骤建框架、此步骤补齐内容。
- 必须明确当前 workflow 不承诺自动修复、自动重试和端到端成功保证。

## out_of_scope
- 不负责真正执行 post-fix。
- 不负责修改 facade registry、发布流程或安装逻辑。
- 不负责新增业务需求或额外实现步骤。
