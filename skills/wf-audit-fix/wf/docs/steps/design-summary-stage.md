# design-summary-stage

## step_slug
`design-summary-stage`

## step_name
结果摘要与交付说明阶段设计

## goal
为 `result_summary` 阶段设计最终摘要、最小验证入口和根文档交付方式，使 workflow 无论成功或失败都能输出一致、可追溯、可继续治理的结果对象。

## inputs
- `design-audit-gate-stage` 在“首次真实目录 audit 即通过”场景下直接交付的终止依据。
- `design-candidate-repair-loop` 在“达到最大尝试次数仍失败”场景下交付的失败原因、尝试日志和最后一次 candidate 诊断。
- `design-promote-and-verify-stage` 交付的 `promote_result`、真实目录最终 audit 结果和最终状态。
- `.lgwf/create_requirements.json` 中已确认的最终摘要要求：至少包含最终 audit 状态、实际尝试次数、最后一次关键诊断、是否发生 candidate promote。
- `04_confirm_business_flow/resources/scaffold_template_spec.md` 和 `scaffold_result_contract.md` 中关于根文档、测试入口和状态边界的约束。

## outputs
- `wf/09_summarize_create_result/workflow.lgwf` 中 summary 节点的设计草案，负责汇总 `entry_decision`、尝试日志、终局状态和关键诊断。
- `wf/09_summarize_create_result/scripts/summarize_create_result.py` 及相关资源/报告占位设计，用于生成结构化 `result_summary` 和人工可读摘要。
- 根 `AGENTS.md`、根 `README.md`、`tests/test_scaffold_package_rules.py`、`tests/README.md` 的职责说明，确保目标 package 初稿具备最小自解释性和验证入口。
- 结构化终局输出契约，至少覆盖 `result_summary`、`final_audit_status`、`attempt_count`、`promote_history`。

## dependencies
- 依赖 `design-audit-gate-stage`、`design-candidate-repair-loop` 和 `design-promote-and-verify-stage` 已统一终局字段命名。
- 若首次真实目录 audit 已通过，本阶段需要支持直接汇总并结束，不依赖 candidate 或 promote 结果存在。
- 本阶段是整个 workflow 的结束阶段，不自动启动下游 workflow，也不自动执行自我优化链路。

## implementation_suggestions
- 在 `wf/09_summarize_create_result/workflow.lgwf` 内把 summary 作为 promote 与复检后的终局收敛节点，同时兼容首轮通过和循环失败两种早停输入。
- 根 `README.md` 与 `AGENTS.md` 说明 workflow 定位、输入输出、运行方式、验证命令和禁止事项，保持中文表达与 UTF-8 编码。
- `tests/test_scaffold_package_rules.py` 优先覆盖路径规则、关键文件存在性、`wf/` 唯一 root 和 `ws/.lgwf` 状态边界，不承诺业务 happy path。
- 人工可读报告可输出到 `reports/create-workflow/create_result_report.md` 或等价位置，但运行状态仍只写入 `ws/.lgwf`。

## acceptance_notes
- 必须保证成功和失败两类终局都输出一致的关键字段，不让调用方依赖分支特例。
- 必须明确根 `SKILL.md` 默认不生成；只有后续确认 `package_profile=skill_wrapped_workflow` 时才新增该文件。
- 必须把 facade 接入说明限制在文档和最小验证层面，不在本阶段直接设计自动注册、自动发布或自动下游触发。

## out_of_scope
- `lgwf-wf-prompt-fix` 集成。
- `lgwf-wf-tools` 自动注册、自动发布或运行时代理实现。
- 自动修复、自动重试和端到端运行保证。
- 自动启动 `wf-post-fix` 或自我优化链路。
