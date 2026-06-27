# Prompt Upgrade Design Spec

`lgwf_wf_prompt_upgrade` 的职责是为目标 LGWF workflow 的 prompt 生成“设计升级方案”，并在人工确认后再应用升级。它不是基础规范检查器；基础格式、引用、输出 JSON 稳定性等问题应优先交给 `lgwf-wf-prompt-fix`。

## Upgrade Goal

升级方案必须回答：这些 prompt 如何更好地驱动目标 workflow 产生高质量结果。重点检查和设计：

1. 目标职责是否清晰：每个 prompt 所在 node 的业务目标、决策边界和禁止事项是否明确。
2. 上下游是否对齐：输入 artifact、workflow node config、输出 artifact、后续消费方是否一致。
3. 角色是否具体：需要哪些领域知识、工程知识、工具能力和审查职责。
4. 输出契约是否可执行：字段、结构、状态枚举、错误/阻塞表达、可追踪证据是否明确。
5. 质量指标是否客观：是否定义可观察、可验收、可拒绝的标准。
6. 失败模式是否覆盖：证据不足、需求不清、越权修改、范围扩大、用户确认缺失时如何处理。
7. 升级是否可落地：必须给出文件级修改计划、风险控制和验收方式。

## Upgrade Value Scoring

不是每个可改进点都应该进入升级方案。每个候选升级必须按以下维度评分，分值使用 `1`、`2`、`3`：

- `impact`: 对目标 workflow 产出质量、稳定性或可验收性的影响。
- `confidence`: 证据是否足够，是否能从 prompt、workflow node 或上下游 artifact 直接支撑。
- `user_value`: 用户确认后能获得的实际能力提升是否清楚。
- `implementation_cost`: 修改复杂度和引入回归风险，`1` 表示低成本，`3` 表示高成本。
- `risk`: 越权、范围扩大、输出契约漂移或破坏上下游的风险，`1` 表示低风险，`3` 表示高风险。

进入 `prompt_upgrades[]` 的候选通常应满足：

- `impact >= 2`
- `confidence >= 2`
- `user_value >= 2`
- `risk <= 2`

不满足条件但值得记录的候选必须进入 `deferred_upgrades[]`，并说明延后原因。不要为了显得全面而把低价值或证据不足的建议包装成升级项。

## ReAct Contract

- `REASON` 只分析现状和升级机会，写 `.lgwf/prompt_upgrade/analysis.json`。
- `ACT` 只生成升级方案，写 `.lgwf/prompt_upgrade/proposal.json`，不得修改目标文件。
- `OBSERVE` 只复核方案质量，写 `.lgwf/prompt_upgrade/proposal_review.json`，不得修改目标文件。
- 只有后续 `confirm_prompt_upgrade` 被用户 approve 后，`apply_prompt_upgrade` 才能修改文件。

## Minimum Proposal Quality

`proposal.json` 至少包含：

- `summary`
- `target_outcome`
- `prompt_upgrades[]`
- `files_to_modify[]`
- `quality_metrics[]`
- `acceptance_checks[]`
- `risks[]`
- `deferred_upgrades[]`

每个 `prompt_upgrades[]` 至少包含：

- `id`
- `prompt_path`
- `workflow_path`
- `node_id`
- `react_phase`
- `current_gap`
- `upgrade_intent`
- `role_design`
- `responsibilities`
- `required_knowledge`
- `required_tools`
- `output_contract_changes`
- `before_contract`
- `after_contract`
- `non_goals`
- `tradeoffs`
- `value_score`
- `quality_metrics`
- `planned_changes`
- `acceptance_checks`
- `risk_controls`

## Constraints

- 不修改 `.lgwf/` runtime artifacts，除本 workflow 要求写入的 `.lgwf/prompt_upgrade/*.json`。
- 默认不修改 `lgwf_wf_prompt_upgrade` 自身文件；只有当 `target_package_root` 明确指向本 workflow package，且用户确认该目标后，才允许把自身 prompt 当作目标 workflow 处理。
- 不把规范检查问题伪装成设计升级；规范问题只作为背景风险记录。
- 不输出泛泛建议；每条升级建议必须能追溯到具体 prompt、workflow node 和可执行修改。
- 不把“更清晰”“更完整”“更详细”作为独立质量指标；质量指标必须可观察、可验收、可拒绝。
