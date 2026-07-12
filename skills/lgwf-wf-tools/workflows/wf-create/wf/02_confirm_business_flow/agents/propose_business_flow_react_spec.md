# propose_business_flow_react 规格

## 职责

`propose_business_flow_react` 负责把需求阶段的稳定输入转成可确认的业务流转 proposal，供 `confirm_business_flow` 和后续步骤设计阶段消费。

## 质量要求

- proposal 必须定义业务阶段、节点命名、阶段依赖和下游输入。
- 输出必须能支撑 `docs/steps` 设计，而不是只复述需求。
- proposal 与 approval 模板字段和节点命名需要对齐。
- 本阶段不直接依赖 `.lgwf/business_flow.json`，该文件只允许在 `confirm_business_flow` 为 `approve` 后固化。

## 必含字段

- `workflow_id`
- `workflow_name`
- `target_package_root`
- `business_goal`
- `stages`
- `stage_dependencies`
- `downstream_step_inputs`
- `risk_notes`
- `design_rationale`

## 边界

- proposal 只用于确认前审阅。
- `confirm_business_flow` 批准前，不得视为正式业务流转契约。
- `.lgwf/business_flow.json` 只允许在 `confirm_business_flow` 为 `approve` 后固化。
