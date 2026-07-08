# Audit Prompt

Audit Prompt 用于 `observe` slot，或一般 prompt 中 review、audit、validate、score、acceptance gate 任务。它负责独立验收 artifact，并给后续 decide 节点、后续 prompt 或人工消费者提供结构化信号。

## 标准结构

```markdown
# <Audit Task Name>

## Role
## Inputs
## Audit Scope
## Audit Criteria
## Output
## Output Format
## Constraints
```

## 写作规则

- `Role` 说明当前节点是独立审核、验收、验证或评分 agent。
- `Inputs` 必须包含被验收 artifact 和必要参考输入。
- `Audit Scope` 明确本次只审核哪些内容，避免扩大职责。
- `Audit Criteria` 放置证据检查、完成情况检查、格式验收、约束检查、下游兼容性和通过/不通过标准。
- `Output Format` 优先包含结构化 review JSON，便于后续 decide 节点、后续 prompt 或人工消费者读取。
- 默认只写 review/audit 输出，不修改被审 artifact。

推荐 review JSON 形态：

```json
{
  "passed": true,
  "issues": [],
  "summary": "简短验收摘要"
}
```

## Checklist

- 当前 prompt 职责是 review、audit、validate、score 或 acceptance gate。
- `Inputs` 包含被验收 artifact 和必要参考输入。
- `Audit Scope` 明确审核范围。
- `Audit Criteria` 可判定，覆盖证据、完整性、格式、约束和下游兼容性。
- `Output Format` 包含结构化 review JSON，例如 `passed/issues/summary`。
- prompt 明确只写 audit/review 输出，不修改被审 artifact。
- 输出能被后续 decide 节点、后续 prompt 或人工消费者读取。

## 示例

````markdown
# Feature Design Audit

## Role
你是 workflow 中的独立验收 agent，负责审核设计文档是否满足输入需求和格式约束。

## Inputs
- `requirements/feature.md`: 用户需求和业务约束。
- `docs/feature_design.md`: 待验收的正式设计文档。

## Audit Scope
只审核 `docs/feature_design.md` 是否覆盖需求、结构完整、约束清晰，并能被后续实现节点使用。

## Audit Criteria
1. 是否覆盖 `requirements/feature.md` 中的目标和约束。
2. 是否说明接口变化、数据流和风险。
3. 是否存在无法从输入支持的确定性表述。
4. 是否包含后续实现所需的信息。

## Output
将审核说明写入 `reports/feature_design_review.md`。
将结构化审核结果写入 `reports/feature_design_review.json`。

## Output Format
`reports/feature_design_review.json` 必须符合：

```json
{
  "passed": true,
  "issues": [],
  "summary": "简短验收摘要"
}
```

## Constraints
- 只写 review 输出，不修改 `docs/feature_design.md`。
- 每个 issue 必须说明对应的输入缺口、文档问题或约束违反。
````

## 常见错误

- 缺少被验收 artifact。
- `Audit Criteria` 写成抽象建议，无法判定通过或失败。
- 审核 prompt 同时修改原 artifact。
- 输出只有自然语言 review，缺少后续 decide 可读的结构化信号。
