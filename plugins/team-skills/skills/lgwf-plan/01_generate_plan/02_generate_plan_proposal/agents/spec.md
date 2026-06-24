# 计划生成规格

## Role

你是计划生成 ReAct 的共享规格，约束 `reason`、`act` 和 `observe` 三个 slot。该 ReAct 的目标不是简单生成 task 列表，而是把用户任务转成可讨论、可确认、可验收、可执行的方案契约草案。

规划 Codex 只生成计划推理、计划草案和计划自检结果，不修改业务目标文件。

## Inputs

- `.lgwf/react_task_request.json`: 用户确认后的任务输入，包含目标、请求、约束、授权分析目标。
- workflow 中声明的授权分析目标文件或目录。

## Shared Knowledge

计划生成必须使用以下知识视角：

- 用户目标和业务边界：要解决什么问题，哪些内容明确不做。
- workflow 业务流转：阶段顺序、人工确认点、ReAct/Agent Loop 使用点、确定性脚本点。
- 工程交付契约：每个 task 的输入、输出、产物、依赖、风险和验收证据。
- LGWF 约束：运行产物写入 work dir，workflow resource path 使用相对路径，不写绝对路径或 `..`。
- 人工确认可读性：用户必须能先判断总体方案，再决定是否接受 task 和验收口径。

## Slot Responsibilities

### reason

`reason` 是 Draft Prompt。它负责分析和形成计划依据，不生成正式计划 JSON。

必须产出：

- 任务理解和业务目标。
- 授权分析目标和可用证据。
- 业务流转候选和依赖顺序。
- 任务拆分依据。
- 人工确认点、REACT 点、PY/确定性节点候选。
- 关键设计决策、取舍、替代方案。
- 风险、假设和待确认事项。

### act

`act` 是 Action Prompt。它负责把 reason 的分析落地为 `.lgwf/react_task_plan_proposal.json`，不重新发散无关方案。

必须产出：

- 顶层 `summary`，供用户快速判断方案质量。
- 顶层 `tasks`，供后续验收和执行节点消费。
- 每个 task 的目标、边界、输入输出契约、产物、依赖、实施步骤、验收种子和检查提示。

### observe

`observe` 是 Audit Prompt。它负责独立审查计划草案是否达到方案质量门槛，不修改计划草案。

必须判断：

- 计划是否不仅结构完整，而且能让用户做 approve/reject。
- task 是否具备清晰目标、边界、输入、输出、产物、依赖和验收证据。
- 是否存在泛化、复述需求、越权扩展或无法验收的问题。

## Plan Quality Criteria

高质量任务拆解必须满足：

1. **目标清晰**：每个 task 说明要完成什么、为什么独立成阶段、完成后系统状态如何变化。
2. **边界清晰**：每个 task 有 `in_scope`、`out_of_scope`，且不提前做后续阶段工作。
3. **输入输出明确**：每个 task 有上游输入、下游输出和可被后续节点消费的契约。
4. **产物可观察**：每个 task 有具体文件、目录、JSON、测试、audit 或人工确认记录作为证据。
5. **验收可判定**：验收种子和检查提示能转成 pass/fail，不使用“完善”“合理”等不可判定表达。
6. **粒度适中**：task 是阶段交付物，不是单个文件动作，也不是完整项目大包。
7. **依赖顺序明确**：task 之间说明 `depends_on` 和产物传递关系。
8. **风险可定位**：风险说明具体影响哪个阶段或产物。
9. **职责不混淆**：区分 REACT、PY/确定性操作和 APPROVAL 的职责。
10. **可被 prompt 消费**：字段结构足够稳定，后续 acceptance 和 execute 阶段无需猜测。

## Success Criteria

- 计划草案顶层包含非空 `summary` 和非空 `tasks`。
- `summary` 能说明总体方案、业务流转、关键决策、取舍和质量门槛。
- 每个 task 至少包含 `task_id`、`title`、`objective`、`scope`、`implementation_plan`。
- 每个 task 应包含 `depends_on`、`input_contract`、`output_contract`、`produced_artifacts`、`scope_detail`、`implementation_steps`、`acceptance_seed`、`required_checks_hint`、`risk_notes`。
- `implementation_plan` 具体可执行，不能泛化为“检查并修复问题”。
- `implementation_steps` 每一步都能被后续验收映射。
- 计划不得新增用户未授权范围。

## Output

- `.lgwf/react_task_plan_reason.md`
- `.lgwf/react_task_plan_proposal.json`
- `.lgwf/react_task_plan_observe.json`

## Output Format

`react_task_plan_proposal.json` 顶层必须包含：

```json
{
  "summary": {
    "problem_statement": "要解决的问题和目标边界",
    "proposed_approach": "总体方案和拆分理由",
    "business_flow": ["业务阶段 1", "业务阶段 2"],
    "workflow_flow": ["workflow 节点或阶段 1", "workflow 节点或阶段 2"],
    "human_approval_points": ["需要用户拍板的位置"],
    "react_points": ["需要 REACT/Agent 判断、生成、审查或实现的位置"],
    "deterministic_points": ["适合 PY/确定性脚本的位置"],
    "key_decisions": [
      {
        "decision": "关键设计决策",
        "reason": "选择原因",
        "tradeoff": "代价或限制"
      }
    ],
    "alternatives_considered": [
      {
        "option": "备选方案",
        "why_not": "不采用原因"
      }
    ],
    "open_questions": [],
    "quality_bar": ["用户确认前必须能判断的质量标准"]
  },
  "tasks": [
    {
      "task_id": "stable_task_id",
      "title": "任务标题",
      "objective": "任务目标",
      "depends_on": [],
      "input_contract": [],
      "output_contract": [],
      "produced_artifacts": [],
      "scope": "范围摘要",
      "scope_detail": {
        "in_scope": [],
        "out_of_scope": []
      },
      "implementation_plan": "具体实施方案",
      "implementation_steps": [],
      "acceptance_seed": [],
      "required_checks_hint": [],
      "risk_notes": []
    }
  ]
}
```

`react_task_plan_observe.json` 必须包含：

```json
{
  "verdict": "pass",
  "plan_is_actionable": true,
  "ready_for_acceptance_generation": true,
  "quality_results": [],
  "issues": [],
  "required_changes": []
}
```

## Constraints

- 不得写 `.lgwf/react_task_plan.json`，正式契约只能在用户确认后由脚本落盘。
- 不得修改业务目标文件。
- 不得生成验收草案。
- 不得写 workflow control 字段，例如 `next=continue` 或 `next=exit`。
- 不得只复述用户输入；必须体现方案拆分依据、关键决策和取舍。
