# LGWF Prompt 辅助

用于设计、优化和验收 LGWF 相关 prompt。先判断 prompt 类型，再读取对应 reference；不要在同一个聚合文件里反复查找 Draft、Action、Audit、Normal 规则。

## 先分流

- **Draft Prompt**：`reason`、`diagnose`、`plan`、草案、方案、候选分析、设计思路。读取 `references/prompt-assist/draft-prompt.md`。
- **Action Prompt**：`act`、修订、落地、转换、生成正式 artifact、应用反馈。读取 `references/prompt-assist/action-prompt.md`。
- **Audit Prompt**：`observe`、review、audit、validate、score、acceptance gate。读取 `references/prompt-assist/audit-prompt.md`。
- **Decide**：默认不是 prompt。`REACT decide` 优先使用脚本或轻量节点写入 `next=continue|exit`；`AGENT_LOOP DECIDE` 优先使用脚本输出 `category`、`reason`、可选 `evidence` 和 `stop_reason`。
- **Normal Prompt**：不属于 Draft、Action、Audit 或 Decide 的普通执行型 prompt，可用于 workflow 中的普通 `exec.codex_prompt`，也可用于 skill reference、调试指南、操作提示等一般 Markdown prompt。通常用于生成、转换、汇总、修订或落地正式 artifact。读取 `references/prompt-assist/normal-prompt.md`。

## 共享规则

所有类型都必须遵守 `references/prompt-assist/shared-rules.md`。如果当前任务只需要判断或优化单一类型，读取对应类型 reference 加 shared rules 即可，不要额外加载其他类型文件。只有当 prompt 被 workflow 节点执行时，才额外检查 workflow 对齐规则。

## 创建或编辑 Prompt

1. 读取目标 prompt；如果它属于 workflow 节点，同时读取相关 `workflow.json` node config。
2. 根据职责选择 Draft、Action、Audit 或 Normal；`decide` 默认优先脚本或轻量节点。
3. 读取对应 reference 文件和 `references/prompt-assist/shared-rules.md`。
4. 按该类型的公式、规则、checklist 和示例优化 prompt。

## 验收 Prompt 文件

1. 读取待验收 prompt；如果它属于 workflow 节点，同时读取相关 `workflow.json` node config。
2. 读取 `references/prompt-assist/prompt-audit-checklist.md` 和 `references/prompt-assist/shared-rules.md`。
3. 如果能判断 prompt 类型，再读取对应的 `references/prompt-assist/draft-prompt.md`、`references/prompt-assist/action-prompt.md`、`references/prompt-assist/audit-prompt.md` 或 `references/prompt-assist/normal-prompt.md`。
4. 按 checklist 输出验收结论，不修改被验收 prompt，除非用户明确要求修订。

默认使用 Markdown 编写 prompt。section heading 可按规范保留英文；正文默认中文，除非用户明确要求其他语言。复杂 prompt 可以用 XML tags 分隔上下文、示例和输出格式，但不强制。
