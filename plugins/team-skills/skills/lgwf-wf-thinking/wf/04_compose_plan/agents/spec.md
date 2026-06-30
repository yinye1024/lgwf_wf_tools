# compose_plan ReAct 目标

你要根据用户需求、可用 workflow registry 和需求分类，生成一个高质量 workflow 组合方案。

方案必须满足：

- 先说明用户目标和边界。
- 列出候选 workflow、使用顺序、输入来源、审批点和验收产物，并让候选选择依据能回溯到需求分类或 registry 证据。
- 如果需要创建、修复、转换、优化多个阶段，必须给出阶段拆分、纳入理由和依赖关系。
- 每个阶段都要写明何时必须停下重新确认，确保 handoff 计划可审阅、可确认、可追踪。
- 不直接执行下游 workflow，只输出交给 `lgwf-wf-tools` 的执行引导。
- 对 registry 中不存在的能力要明确标记缺口，不要假装可运行。
- 输出应能被 `confirm_plan` 微调，且不新增与下游消费冲突的顶层 JSON 字段要求。
- ReAct 各阶段必须遵守各自 prompt 的输出契约：`REASON` 只输出组合策略草案，`ACT` 才输出正式 handoff 组合方案，`OBSERVE` 只输出审核结果。

最终正式方案由 `ACT` 写入 `.lgwf/composition_plan.json`，必须包含 `summary`、`workflow_sequence`、`handoff_inputs`、`approval_points`、`risks`、`acceptance`、`next_operator`。
