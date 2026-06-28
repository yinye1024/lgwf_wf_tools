# 步骤设计文档目录

这里存放 `design_steps_react` 生成的步骤设计文档草案。每份文档都是 `confirm_step_designs` 的审阅对象，也是 `implement_steps_react` 的直接输入契约。

## 命名约定

- 每个步骤文档使用 `docs/steps/<step-slug>.md`。
- `step-slug` 使用 kebab-case，并与业务流转中的 `downstream_step_inputs[].step_slug` 保持一致。
- 不要使用空格、中文标点或临时编号作为文件名。

## 必含字段

每份步骤设计文档至少覆盖以下字段：

- `step_slug`
- `step_name`
- `goal`
- `inputs`
- `outputs`
- `dependencies`
- `implementation_suggestions`
- `acceptance_notes`
- `out_of_scope`

这些字段必须能被 `implement_steps_react` 直接消费，避免设计文档与实现接口脱节。

## 内容要求

- `goal`：说明该步骤的目标和业务价值。
- `inputs`：列出上游阶段、文件、状态或约束。
- `outputs`：说明会生成哪些 workflow 初稿文件、目录或结构片段。
- `dependencies`：写清前置步骤、依赖节点和人工确认点。
- `implementation_suggestions`：记录实现方向、建议文件位置和关键约束。
- `acceptance_notes`：标记人工审查时要重点核对的内容。
- `out_of_scope`：明确排除 `lgwf-wf-prompt-fix`、`lgwf-wf-agent`、自动修复和端到端运行保证。

## 当前 run 边界

- 当前 run 只验证文档模板、命名约定和接口可消费性。
- `.lgwf/step_designs.json` 只允许在 `confirm_step_designs` 为 `approve` 后固化。
- 当前 run 不要求真实落盘完整步骤设计文档结果。

模板见 `step-design-template.md`。
