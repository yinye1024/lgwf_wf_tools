# Normal Prompt

Normal Prompt 用于不属于 Draft、Action、Audit 或 Decide 的普通执行型 prompt。它可用于 workflow 中的普通 `exec.codex_prompt`，也可用于 skill reference、调试指南、操作提示等一般 Markdown prompt。它通常负责生成、转换、汇总、修订或落地一个正式 artifact，规范与 Action Prompt 保持一致。

如果 prompt 的职责本身是草案、方案、候选分析或设计思路，应使用 Draft Prompt；如果职责是独立审核、验收、验证或评分，应使用 Audit Prompt；如果它处在 ReAct `act` slot，应使用 Action Prompt；如果它只是判断 workflow 是否继续，应优先用 Decide 脚本或轻量节点。

## 适用范围

- workflow 中不属于 Draft、Action 或 Audit 职责的普通 `exec.codex_prompt`。
- skill reference、调试指南、操作提示、开发指南等需要指导 agent 执行任务的 Markdown prompt。
- 生成、转换、汇总、修订或落地正式 artifact 的执行型文档。
- 不适用于独立验收 prompt；验收职责使用 Audit Prompt。

## 标准结构

```markdown
# <Normal Task Name>

## Role
## Inputs
## Task
## Success Criteria
## Output
## Output Format
## Constraints
```

## 写作规则

- `Role` 说明当前 prompt 负责生成、转换、汇总、修订或落地正式 artifact。
- `Inputs` 列出当前任务需要读取的文件、目录、上下文或前序产物。
- `Task` 明确要完成的实际工作，不写审核职责。
- `Success Criteria` 描述正式产物完成条件，不描述独立验收标准。
- `Output` 指向正式 artifact 或明确的修改文件范围。
- `Output Format` 必须足够具体，确保下游节点能稳定读取。
- 不承担独立验收职责，不输出通过/不通过判断。
- 不写 workflow control 字段，例如 `next=continue|exit`，除非该 prompt 明确就是控制流决策文档；这类情况优先改用 Decide。

## Workflow 使用时额外要求

- 如果 Normal Prompt 被 workflow 节点执行，`Inputs` 必须与当前 node 的 `context_refs` 对齐，或明确来自前序节点输出。
- workflow 中的输入和输出路径使用 workspace-relative path 或 workflow-relative path，不使用绝对路径或 `..`。
- prompt 不要求 runtime 读取 client package 或 workspace 文件；资源读取由 client/Codex 完成。
- `Output` 必须能被下游 node、脚本或人工消费者稳定读取。

## Checklist

- 当前 prompt 是普通执行型 prompt，且不属于 Draft、Action、Audit 或 Decide 职责。
- prompt 职责是生成、转换、汇总、修订或落地正式 artifact。
- `Inputs` 明确列出任务需要的上下文、文件、目录或前序产物。
- `Output` 指向正式 artifact 或指定修改范围。
- `Output Format` 能被下游消费。
- prompt 没有输出 review JSON 或通过/不通过判断。
- prompt 没有写 `next=continue|exit`。
- 如果用于 workflow 节点，`Inputs` 与 `context_refs` 或前序节点输出对齐。

## 示例

```markdown
# Final Report Generation

## Role
你是正式报告生成 agent，负责根据多个前序分析结果生成最终报告。

## Inputs
- `reports/item_1/analysis.md`: 第一个候选项分析。
- `reports/item_2/analysis.md`: 第二个候选项分析。
- `data/summary.json`: 输入数据摘要和计算口径。

## Task
1. 汇总多个候选项的关键信息。
2. 比较差异、风险和不确定性。
3. 生成正式最终报告。

## Success Criteria
- 正式报告覆盖所有输入候选项。
- 结论能追溯到输入文件。
- 输出结构能被后续脚本或人工读取。

## Output
将正式报告写入 `reports/final_report.md`。

## Output Format
使用 Markdown，包含：背景、输入摘要、对比表、结论、风险、待确认事项。

## Constraints
- 只写入 `reports/final_report.md`。
- 不输出验收结论。
- 不写 workflow control 字段。
```

## 常见错误

- 把普通执行型 prompt 错误归类成 ReAct `act` slot。
- 把普通 skill reference 错误要求必须存在 `workflow.json` 或 `context_refs`。
- 缺少 `Success Criteria` 或 `Output Format`。
- 输出路径不明确，导致下游节点无法读取。
- 在普通 prompt 中写 review JSON 或 `next=continue|exit`。
