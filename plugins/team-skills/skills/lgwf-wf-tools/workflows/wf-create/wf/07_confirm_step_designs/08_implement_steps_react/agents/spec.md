# implement_steps_react 规格

## 职责

`implement_steps_react` 负责根据已确认的步骤设计文档生成目标 workflow package 的初稿文件与目录，确保产物可继续进入后续验收，但不承诺完整运行能力。

## 质量要求

- 实现阶段必须严格消费 `docs/steps/*.md` 的输入契约，不得脱离已确认设计自行扩 scope。
- 输出必须清楚对应到 workflow 初稿文件、目录和占位内容，而不是停留在抽象描述。
- 相对路径、work dir 边界和中文 UTF-8 文档基线必须继续成立。
- 当前阶段明确排除 `lgwf-wf-prompt-fix`、`lgwf-wf-tools`、自动修复和端到端运行保证。

## 关键输入

- 已确认的步骤设计文档。
- 每份文档中的 `step_slug`、`inputs`、`outputs`、`dependencies`、`implementation_suggestions`。

## 预期输出

- workflow 初稿目录与文件。
- 对应的 `workflow.lgwf`、`agents/*.md`、`scripts/*.py`、`resources/`、`tests/` 或其他设计文档约定产物。
- 可供后续验收的初稿说明，而不是确认后正式运行状态 JSON。

## 边界

- 只按已确认设计生成 workflow 初稿文件。
- 不生成 prompt 修复链路。
- 不生成 agent 化链路。
- 不做自动修复、自动重试或端到端运行保证。
- 只消费已由 `confirm_step_designs` approve 后固化的 `.lgwf/step_designs.json` 或等价确认记录。
