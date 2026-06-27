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
