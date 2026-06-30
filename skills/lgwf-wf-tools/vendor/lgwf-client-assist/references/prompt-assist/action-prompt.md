# Action Prompt

Action Prompt 用于 ReAct `act` slot。它负责根据草案、前序 artifact 或审核反馈进行修订、落地、转换和正式 artifact 生成，不重新发散。

## 标准结构

```markdown
# <Action Task Name>

## Role
## Inputs
## Task
## Success Criteria
## Output
## Output Format
## Constraints
```

## 写作规则

- `Role` 说明当前节点负责落地、修订、转换或生成正式 artifact。
- `Inputs` 必须包含要消费的 draft、proposal、previous artifact 或 audit feedback。
- `Task` 明确如何处理反馈、如何生成正式 artifact，以及无法处理的反馈如何记录。
- `Success Criteria` 描述正式产物完成条件，不描述独立验收标准。
- `Output` 指向正式 artifact 或明确的修改文件范围。
- `Output Format` 必须足够具体，确保下游节点能稳定读取。
- 不重新发散生成无关方案。
- 不承担验收职责，不输出通过/不通过判断。

## Checklist

- 当前 prompt 职责是落地、修订、转换或生成正式 artifact。
- `Inputs` 包含 draft/proposal/previous artifact 或 audit feedback。
- `Task` 明确处理反馈；无法处理的反馈需要说明。
- `Output` 指向正式 artifact 或指定修改范围。
- `Output Format` 能被下游消费。
- prompt 没有重新生成无关方案。
- prompt 没有输出 review JSON 或通过/不通过判断。

## 示例

```markdown
# Feature Design Finalization

## Role
你是 workflow 中的落地 agent，负责根据设计草案和审核反馈生成正式设计文档。

## Inputs
- `reports/feature_design_draft.md`: 前序节点生成的设计草案。
- `reports/feature_design_review.json`: 审核节点输出的结构化反馈。
- `docs/architecture.md`: 当前系统架构说明。

## Task
1. 根据审核反馈修订设计草案。
2. 生成正式设计文档。
3. 对无法处理的反馈，在文档末尾说明原因。

## Success Criteria
- 正式设计文档结构完整。
- 已处理所有可处理的审核反馈。
- 未处理反馈有明确说明。

## Output
将正式设计文档写入 `docs/feature_design.md`。

## Output Format
使用 Markdown，包含：背景、目标、设计方案、接口变化、风险、未处理反馈。

## Constraints
- 只写入 `docs/feature_design.md`。
- 不重新生成无关方案。
- 不输出验收结论。
```

## 常见错误

- 没有把 draft 或 audit feedback 列为输入。
- 修订节点重新生成全新方案，丢失前序上下文。
- 把正式产物写到草案路径。
- 在 Action Prompt 中要求模型自评通过或决定 workflow 是否继续。
