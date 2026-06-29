# `lgwf-wf-create` 决策草案

## 摘要

新增独立 skill/workflow：`lgwf-wf-create`，用于根据用户的原始意图创建一个 LGWF workflow 初稿。它负责“需求方案、业务流转、目录框架、步骤设计、按设计实现初稿”，但不负责后续 prompt 验收和运行修复。

后续由主 agent 串联：

```text
lgwf-wf-create -> lgwf-wf-prompt-fix -> lgwf-wf-tools
```

## 核心流程

`lgwf-wf-create` 的 workflow 主流程定为：

```text
collect_raw_intent
  -> propose_requirements_react
  -> confirm_requirements
  -> propose_business_flow_react
  -> confirm_business_flow
  -> scaffold_package
  -> design_steps_react
  -> confirm_step_designs
  -> implement_steps_react
  -> summarize_create_result
```

含义：

- `collect_raw_intent`：只收集用户原始意图，不要求用户填写完整结构化 JSON。
- `propose_requirements_react`：agent 用 `REACT` 生成需求方案。
- `confirm_requirements`：用户确认或修改需求方案。
- `propose_business_flow_react`：agent 用 `REACT` 设计目标 workflow 的业务流转逻辑。
- `confirm_business_flow`：用户确认业务流转。
- `scaffold_package`：确定性创建目标 workflow 目录和文件框架。
- `design_steps_react`：agent 用 `REACT` 为每个步骤生成设计文档。
- `confirm_step_designs`：用户确认步骤设计文档。
- `implement_steps_react`：agent 用 `REACT` 按设计文档实现初稿。
- `summarize_create_result`：确定性汇总创建结果。

## 关键设计决策

所有需要 agent 判断、生成、审查或实现的地方，统一使用 `REACT`：

- 需求方案生成使用 `REACT`。
- 业务流转设计使用 `REACT`。
- 步骤设计文档生成使用 `REACT`。
- 按设计实现初稿使用 `REACT`。

只在确定性操作中使用 `PY`：

- 创建目录框架。
- 校验必要文件是否存在。
- 汇总创建结果。

只在需要用户拍板时使用 `APPROVAL`：

- 确认需求方案。
- 确认业务流转。
- 确认步骤设计文档。

## 需求确认方式

第 1 步不是让用户填写完整表单，而是：

```text
用户原始意图 -> agent 生成需求方案 -> 用户确认/修改 -> 固化需求
```

需求方案至少包含：

```json
{
  "workflow_name": "目标 workflow 名称",
  "target_package_root": "目标 workflow package 目录",
  "purpose": "用途",
  "target_users": ["目标用户"],
  "expected_inputs": ["预期输入"],
  "expected_outputs": ["预期输出"],
  "human_approvals": ["需要人工确认的节点"],
  "workflow_shape": "simple | react | agent_loop",
  "reasoning": "为什么这样设计"
}
```

用户确认节点支持三种结果：

```json
{
  "decision": "approve",
  "changes": []
}
```

```json
{
  "decision": "revise",
  "changes": ["需要修改的点"]
}
```

```json
{
  "decision": "reject",
  "reason": "拒绝原因"
}
```

## 目标输出

`lgwf-wf-create` 成功后，应在目标目录生成一个可继续验收的 workflow package 初稿，包括：

- `SKILL.md`
- `README.md`
- `workflow.lgwf`
- 阶段目录，例如 `00_confirm_request/`、`01_prepare/`、`02_execute/`、`03_summary/`
- 必要的 `agents/*.md`
- 必要的 `scripts/*.py`
- `tests/` 最小测试或占位测试
- 每个 workflow 步骤的设计文档，例如 `docs/steps/*.md`

`lgwf-wf-create` 自己的运行产物写入它自己的 work dir，例如：

```text
plugins/team-skills/skills/lgwf-wf-create/ws/.lgwf/
```

建议核心产物：

- `.lgwf/raw_intent.json`
- `.lgwf/create_requirements_proposal.json`
- `.lgwf/create_requirements.json`
- `.lgwf/business_flow_proposal.json`
- `.lgwf/business_flow.json`
- `.lgwf/scaffold_result.json`
- `.lgwf/step_designs.json`
- `.lgwf/create_summary.json`

## 明确不做

第一版 `lgwf-wf-create` 不做这些事：

- 不调用 `lgwf-wf-prompt-fix`。
- 不调用 `lgwf-wf-tools`。
- 不保证目标 workflow 能端到端运行成功。
- 不自动修复 prompt 质量问题。
- 不自动循环修复运行失败。
- 不把主 agent 串联逻辑写死进 `lgwf-wf-create`。

## 验收方式

第一版完成后，至少验证：

- `lgwf-wf-create` 自身 `workflow.lgwf` 通过 `lgwf.py audit`。
- 启动后能进入原始意图收集和需求确认节点。
- 确认需求后能生成业务流转方案。
- 确认业务流转后能创建目标目录框架。
- 确认步骤设计后能生成目标 workflow 初稿文件。
- 生成的 Markdown 文档默认使用中文。
- 生成的 workflow resource path 使用相对路径，不写绝对路径或 `..`。
- 运行产物只写入 work dir，不污染目标 package 的 `.lgwf` 运行状态。

## 默认假设

- `lgwf-wf-create` 放在 `plugins/team-skills/skills/lgwf-wf-create`。
- 它作为独立 team skill 暴露，不修改 `lgwf-plan`。
- 第一版目标是“初稿可进入后续验收”，不是“自动完成可用 workflow”。
- 后续主 agent 串联策略在三个 workflow 都稳定后再单独设计。
