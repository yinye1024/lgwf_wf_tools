# Draft Prompt

Draft Prompt 用于 `reason` slot，或一般 prompt 中生成草案、方案、候选分析、设计思路的任务。它只负责形成可供后续节点、后续 prompt 或人工消费者使用的中间 artifact，不做验收。

## 标准结构

```markdown
# <Draft Task Name>

## Role
## Inputs
## Task
## Success Criteria
## Output
## Output Format
## Constraints
```

## 写作规则

- `Role` 说明当前节点负责生成草案或方案，不写审核职责。
- `Inputs` 列出源数据、需求、上下文文件或目录。
- `Task` 要求生成初稿、候选方案、分析框架、设计思路或计划。
- `Success Criteria` 描述草案完成条件，不描述验收通过条件。
- `Output` 通常写入 draft、proposal、plan、analysis_draft 等草案 artifact。
- 可以记录假设、取舍和待确认事项。
- 不覆盖正式 artifact，除非 workflow 明确把该节点定义为正式产出。
- 不输出 review JSON，不写 `passed/issues/summary`。
- 不写 workflow control 字段，例如 `next=continue|exit`。

## Checklist

- 当前 prompt 职责是生成草案、方案、候选分析或设计思路。
- 输出路径体现 draft/proposal/plan 等草案属性。
- 草案能被后续 Action Prompt、Normal Prompt 或人工消费者直接读取。
- prompt 没有要求修改正式 artifact。
- prompt 没有要求自我验收、评分或决定是否继续。
- prompt 没有写 `next=continue|exit`。

## 示例

```markdown
# Feature Design Draft

## Role
你是 workflow 中的方案草案 agent，负责根据输入需求生成可供后续落地节点使用的设计草案。

## Inputs
- `requirements/feature.md`: 用户需求和业务约束。
- `docs/architecture.md`: 当前系统架构说明。

## Task
1. 提炼需求目标和关键约束。
2. 给出一个可实施的设计草案。
3. 标注设计假设、风险和待确认事项。

## Success Criteria
- 草案覆盖需求目标、主要模块、数据流和风险。
- 草案可被后续 Action Prompt、Normal Prompt 或人工消费者直接读取和落地。

## Output
将设计草案写入 `reports/feature_design_draft.md`。

## Output Format
使用 Markdown，包含：目标、方案概述、模块影响、数据流、风险、待确认事项。

## Constraints
- 不修改代码或正式文档。
- 不覆盖正式设计文件。
- 不执行验收或评分。
```

## 常见错误

- 把草案直接写到正式产物路径。
- 在草案 prompt 中要求模型判断自己是否通过验收。
- 把审核标准写进生成节点，让生成节点自我审计。
- 在 Draft Prompt 中写 workflow control 字段。
