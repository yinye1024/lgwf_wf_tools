# design_steps_react 规格

## 职责

`design_steps_react` 负责把已确认的业务流转与脚手架约束转换成可确认的 `docs/steps/*.md` 步骤设计文档草案，供 `confirm_step_designs` 审阅，并供 `implement_steps_react` 直接消费。

## 质量要求

- 输出必须是稳定、可审阅、可追踪的步骤设计文档，而不是泛化说明。
- 文档字段、命名和存放约定必须与 `implement_steps_react` 输入契约一致。
- 每个步骤都要写清目标、输入、输出、依赖和实现建议，避免下游实现阶段继续猜测。
- 本阶段不直接依赖 `.lgwf/step_designs.json`，该文件只允许在 `confirm_step_designs` 为 `approve` 后固化。

## 必含字段

- `step_slug`
- `step_name`
- `goal`
- `inputs`
- `outputs`
- `dependencies`
- `implementation_suggestions`
- `acceptance_notes`
- `out_of_scope`

## 命名与存放约定

- 文档路径使用 `docs/steps/<step-slug>.md`。
- `step_slug` 使用 kebab-case，并与业务流转中的 `downstream_step_inputs[].step_slug` 保持一致。
- 文档使用 UTF-8 Markdown，主要说明文字默认使用中文。

## 边界

- 设计文档只用于确认前审阅。
- `confirm_step_designs` 批准前，不得视为正式步骤设计契约。
- `.lgwf/step_designs.json` 只允许在 `confirm_step_designs` 为 `approve` 后固化。
- 不得把 `lgwf-wf-prompt-fix`、`lgwf-wf-tools`、自动修复或端到端运行保证写成当前阶段必需项。
