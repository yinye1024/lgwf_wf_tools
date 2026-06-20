# guide.md

# LGWF Prompt 辅助

用于设计、优化和验收 LGWF 相关 prompt。先判断 prompt 类型，再读取对应 reference；不要在同一个聚合文件里反复查找 Draft、Action、Audit、Normal 规则。

## 先分流

- **Draft Prompt**：`reason`、草案、方案、候选分析、设计思路。读取 `references/prompt-assist/draft-prompt.md`。
- **Action Prompt**：`act`、修订、落地、转换、生成正式 artifact、应用反馈。读取 `references/prompt-assist/action-prompt.md`。
- **Audit Prompt**：`observe`、review、audit、validate、score、acceptance gate。读取 `references/prompt-assist/audit-prompt.md`。
- **Decide**：默认不是 prompt。优先使用脚本或轻量节点写入 `next=continue|exit`。
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



---

# prompt-audit-checklist.md

# Prompt Audit Checklist

用于验收 LGWF prompt 文件本身，包括 workflow 节点 prompt 和普通执行型 Markdown prompt。它不是业务 workflow 的 `observe` 节点规范；业务 artifact 审核仍使用 `audit-prompt.md`。

验收 prompt 时，先读取本 checklist 和 `shared-rules.md`。如果能判断 prompt 类型，再读取对应的 `draft-prompt.md`、`action-prompt.md`、`audit-prompt.md` 或 `normal-prompt.md`。

## Routing Checklist

- 已根据职责判断 prompt 类型：Draft、Action、Audit、Normal 或 Decide。
- `reason`、草案、方案、候选分析映射为 Draft Prompt。
- `act`、修订、落地、转换、正式 artifact 映射为 Action Prompt。
- `observe`、review、audit、validate、score、acceptance gate 映射为 Audit Prompt。
- `decide` 默认不是 prompt，优先脚本或轻量节点写入 `next=continue|exit`。
- 不属于 Draft、Action、Audit 或 Decide 的普通执行型 prompt，映射为 Normal Prompt。
- 没有在同一个 prompt 中混合生成、落地、审核和决策职责。

## Shared Rules Checklist

- `Inputs` 明确列出任务需要的上下文、文件、目录或前序产物。
- `Output` 能被下游 node、脚本或人工消费者稳定读取。
- prompt 只写指定输出路径或指定文件范围。
- 输出格式足够具体，避免下游节点依赖自然语言猜测。
- 如果 prompt 属于 workflow 节点，`Inputs` 与当前 node 的 `workflow.json` `context_refs` 对齐，或明确来自前序节点输出。
- 如果 prompt 属于 workflow 节点，需要读取的 workspace 文件或目录都能从 `context_refs` 找到。
- 如果 prompt 属于 workflow 节点，输入和输出路径使用 workspace-relative path 或 workflow-relative path，不使用绝对路径或 `..`。
- 如果 prompt 属于 workflow 节点，不要求 runtime 读取 client package 或 workspace 文件。

## Draft Prompt Checklist

- prompt 职责是生成草案、方案、候选分析、设计思路或计划。
- 标准结构包含 `Role`、`Inputs`、`Task`、`Success Criteria`、`Output`、`Output Format`、`Constraints`。
- 输出路径体现 draft、proposal、plan 或 analysis_draft 等草案属性。
- 草案能被后续 Action Prompt 直接读取。
- 不覆盖正式 artifact，除非 workflow 明确把该节点定义为正式产出。
- 不要求自我验收、评分或通过/不通过判断。
- 不输出 review JSON，不写 `passed/issues/summary`。
- 不写 workflow control 字段，例如 `next=continue|exit`。

## Action Prompt Checklist

- prompt 职责是修订、落地、转换、应用反馈或生成正式 artifact。
- 标准结构包含 `Role`、`Inputs`、`Task`、`Success Criteria`、`Output`、`Output Format`、`Constraints`。
- `Inputs` 包含 draft、proposal、previous artifact 或 audit feedback。
- `Task` 明确如何处理反馈；无法处理的反馈需要记录原因。
- `Output` 指向正式 artifact 或指定修改文件范围。
- 不重新发散生成无关方案。
- 不承担验收职责，不输出通过/不通过判断。
- 不输出 review JSON，不写 `passed/issues/summary`。

## Normal Prompt Checklist

- 当前 prompt 是普通执行型 prompt，且不属于 Draft、Action、Audit 或 Decide 职责。
- 标准结构包含 `Role`、`Inputs`、`Task`、`Success Criteria`、`Output`、`Output Format`、`Constraints`。
- prompt 职责是生成、转换、汇总、修订或落地正式 artifact。
- `Inputs` 明确列出任务需要的上下文、文件、目录或前序产物。
- `Output` 指向正式 artifact 或指定修改范围。
- `Output Format` 能被下游消费。
- prompt 没有输出 review JSON 或通过/不通过判断。
- prompt 没有写 `next=continue|exit`。

## Normal Prompt Workflow Addendum

- 如果 Normal Prompt 被 workflow 节点执行，`Inputs` 与当前 node 的 `context_refs` 或前序节点输出对齐。
- 如果 Normal Prompt 被 workflow 节点执行，prompt 需要读取的 workspace 文件或目录都能从 `context_refs` 找到。
- 如果 Normal Prompt 被 workflow 节点执行，`Output` 使用可被下游读取的 workspace-relative path 或 workflow-relative path。
- 如果 Normal Prompt 被 workflow 节点执行，prompt 不要求 runtime 读取 client package 或 workspace 文件。

## Audit Prompt Checklist

- prompt 职责是独立 review、audit、validate、score 或 acceptance gate。
- 标准结构包含 `Role`、`Inputs`、`Audit Scope`、`Audit Criteria`、`Output`、`Output Format`、`Constraints`。
- `Inputs` 包含被验收 artifact 和必要参考输入。
- `Audit Scope` 明确本次只审核哪些内容。
- `Audit Criteria` 可判定，覆盖证据、完整性、格式、约束和下游兼容性。
- `Output Format` 包含结构化 review JSON，例如 `passed/issues/summary`。
- prompt 明确只写 audit/review 输出，不修改被审 artifact。
- 输出能被后续 decide 节点读取。

## Language Checklist

- 正文默认中文，除非用户明确要求其他语言。
- section heading 可按规范保留英文。
- 代码标识符、JSON/YAML key、DSL 字段、路径、命令、API 名称保持原文。
- 代码注释默认中文，除非目标文件或外部规范要求其他语言。
- 不把某个领域的专门约束写成所有 workflow 的默认规则。

## Review Output

验收输出建议使用结构化摘要，便于人工或后续节点读取：

```json
{
  "passed": true,
  "issues": [],
  "summary": "简短验收摘要"
}
```

`issues` 中的每一项应说明问题位置、违反的 checklist 项和建议修正方向。



---

# shared-rules.md

# 共享规则

所有 LGWF prompt 类型都必须遵守这些规则。类型专属规则只读取对应 reference：`draft-prompt.md`、`action-prompt.md`、`audit-prompt.md` 或 `normal-prompt.md`。workflow 对齐规则只适用于被 workflow 节点执行的 prompt。

## 通用规则

- `Inputs` 明确列出任务需要的上下文、文件、目录或前序产物。
- `Output` 指向正式 artifact、草案 artifact、review 输出或指定修改范围。
- `Output Format` 足够具体，避免下游节点、脚本或人工消费者依赖自然语言猜测。
- prompt 只写指定输出路径或指定文件范围。
- 不在同一个 prompt 中混合生成、落地、审核和决策职责。

## Workflow 对齐

- `Inputs` 使用 workspace-relative path。
- `Inputs` 必须与当前 node 的 `workflow.json` `context_refs` 对齐，或明确来自前序节点输出。
- `Output` 使用 workspace-relative path。
- `Output` 必须能被下游 node、脚本或人工消费者稳定读取。
- prompt 不要求 runtime 读取 client package 或 workspace 文件；资源读取由 client/Codex 完成。
- prompt 只写指定输出路径或指定文件范围。

## 语言和格式

- 默认使用 Markdown 编写 prompt。
- section heading 可按规范保留英文。
- 正文默认中文，除非用户明确要求其他语言。
- 复杂 prompt 可以使用 XML tags 分隔上下文、示例和输出格式，但不强制。
- Normal Prompt 是不属于 Draft、Action、Audit 或 Decide 的普通执行型 prompt，规范与 Action Prompt 保持一致。workflow 中的普通 `exec.codex_prompt` 是 Normal Prompt 的一个特例。

## ReAct 映射

- `reason` 使用 Draft Prompt。
- `act` 使用 Action Prompt。
- `observe` 使用 Audit Prompt。
- `decide` 默认使用脚本或轻量节点，读取 audit 结果并写入 `next=continue|exit`。

## 领域约束

领域特定约束只在 workflow 明确需要时添加。例如金融、医疗、法律、安全等高风险领域，应在对应 prompt 的 `Constraints` 或 Audit Prompt 的 `Audit Criteria` 中加入专门限制。不要把某个领域的约束作为所有 workflow 的默认规则。

