# propose_requirements_react 规格

## 职责

`propose_requirements_react` 负责生成可确认的 `create_requirements_proposal`，作为后续 `confirm_requirements` 和业务流转设计的输入契约。

## 质量要求

- 字段结构稳定，可被下游阶段消费。
- 设计理由清楚，不只是宽泛摘要。
- proposal 与 approval 模板字段对齐。
- 当前 run 不依赖 confirmed requirements artifact。

## 必含字段

- `workflow_name`
- `target_package_root`
- `purpose`
- `target_users`
- `expected_inputs`
- `expected_outputs`
- `human_approval_points`
- `workflow_shape`
- `proposal_notes`
- `design_rationale`

## 边界

- proposal 仅用于确认前审阅。
- `confirm_requirements` 批准前，不得视为正式需求契约。
- `.lgwf/create_requirements.json` 只允许在 `confirm_requirements` 为 `approve` 后固化。
