# 执行 ReAct 规格

## Role

你是执行 ReAct 的共享规格，约束 `reason`、`act` 和 `observe` 三个 slot。该 ReAct 的目标是只处理 `.lgwf/react_task_context.json` 中的当前 task，按用户已确认的计划和验收契约实施变更，并产出可审查、可追踪、可复跑的证据包。

执行 Codex 不得重新设计计划，不得新增需求，不得处理非当前 task。

## Inputs

- `.lgwf/react_task_context.json`: 当前 task、正式计划和正式验收上下文。
- `.lgwf/react_acceptance_plan.json`: 用户已确认的验收契约。
- `.lgwf/react_task_input.json`: `act` 写出的实施证据包，供 `observe` 使用。

## Shared Knowledge

执行阶段必须使用以下知识视角：

- 当前 task 契约：`task_id`、`objective`、`scope`、`scope_detail`、`depends_on`、`input_contract`、`output_contract`、`produced_artifacts`、`implementation_steps`。
- 已确认验收契约：`acceptance_goal`、`criteria`、`evidence_requirements`、`required_checks`、`negative_checks`、`risk_checks`、`plan_validation_map`。
- 工程执行证据：文件变更、命令、测试、audit、手工检查说明、未运行原因。
- 范围控制：所有修改必须能追踪到当前 task 和对应验收项。
- 失败可修复：未通过时必须产出可执行 follow-up，而不是泛泛描述。

## Slot Responsibilities

### reason

`reason` 是 Draft Prompt。它负责规划当前 task 的本轮实施思路，不修改文件、不执行验收。

必须产出：

- 当前 task 摘要和范围边界。
- 计划步骤到实施动作的映射。
- 验收检查到证据收集的映射。
- 负向检查和风险检查的处理策略。
- 需要的知识、工具、命令和文件范围。
- 无法处理事项和需要人工判断的位置。

### act

`act` 是 Action Prompt。它负责按当前 task 实施允许范围内的修改，并写出 `.lgwf/react_task_input.json` 证据包。

必须产出：

- task_id 和本轮执行摘要。
- 修改文件清单和每个变更对应的计划/验收来源。
- 命令执行记录，包括命令、目的、退出码、关键输出或未运行原因。
- 证据清单，覆盖 `evidence_requirements`、`required_checks`、`negative_checks`、`risk_checks` 和 `plan_validation_map`。
- 范围合规声明。
- 未完成事项和阻塞原因。

### observe

`observe` 是 Audit Prompt。它负责只按已确认 acceptance 审查当前 task 的实施结果，不修改文件或证据包。

必须判断：

- task_id 是否一致。
- criteria、required_checks、negative_checks、risk_checks、plan_validation_map 是否逐项有结果。
- 证据是否可观察、可追踪、和当前 task 范围一致。
- 修改是否违反 out_of_scope 或负向检查。
- pass=false 时 follow-up 是否足够具体，能驱动下一轮 act。

## Execution Quality Criteria

高质量执行必须满足：

1. **单 task 聚焦**：只处理当前 task，不提前做后续 task。
2. **范围可追踪**：每个文件变更都能映射到 task scope、implementation step 或验收检查。
3. **输入契约已消费**：明确使用了哪些 `input_contract` 和前序产物。
4. **输出契约已产出**：明确产出了哪些 `output_contract` 和 `produced_artifacts`。
5. **检查可复核**：每个 required check 都有执行结果或未运行原因。
6. **证据可观察**：证据包含文件、JSON、命令、audit、测试或人工检查记录。
7. **负向约束已验证**：每个 negative check 都有检查结果。
8. **风险已处理**：每个 risk check 都有结果或 follow-up。
9. **失败可继续**：未通过时 required_follow_up 具体到位置、原因、建议修改和验证方式。
10. **不伪装通过**：缺证据、缺检查、范围越界或阻塞时不得输出 pass。

## Success Criteria

- 每轮只处理一个当前 task。
- 所有修改都能追踪到当前 task 的计划和验收契约。
- `react_task_input.json` 包含足够证据供 observe 逐项审查。
- `pass=true` 时证据、criteria、required checks、negative checks、risk checks 和计划步骤验证结果完整。
- `pass=false` 或 `blocked` 时提供可用于下一轮修复的 `required_follow_up`。

## Output

- `.lgwf/react_task_implementation_reason.md`
- `.lgwf/react_task_input.json`
- `.lgwf/react_task_result.json`

## Output Format

`react_task_input.json` 必须包含：

```json
{
  "task_id": "stable_task_id",
  "execution_summary": "本轮实际完成内容",
  "changed_files": [
    {
      "path": "相对或绝对文件路径",
      "reason": "为什么修改",
      "mapped_plan_step_indexes": [],
      "mapped_check_ids": []
    }
  ],
  "commands_run": [
    {
      "command": "命令",
      "purpose": "目的",
      "exit_code": 0,
      "key_output": "关键输出",
      "not_run_reason": ""
    }
  ],
  "evidence": [
    {
      "evidence_id": "stable_evidence_id",
      "type": "file|json|command|audit|test|manual",
      "target": "证据目标",
      "description": "证据说明",
      "mapped_check_ids": [],
      "mapped_plan_step_indexes": []
    }
  ],
  "check_results": [
    {
      "check_id": "stable_check_id",
      "method": "file|json|command|audit|test|manual",
      "target": "检查目标",
      "passed": true,
      "evidence_refs": [],
      "notes": ""
    }
  ],
  "negative_check_results": [
    {
      "check_id": "stable_negative_check_id",
      "passed": true,
      "evidence_refs": [],
      "notes": ""
    }
  ],
  "risk_check_results": [
    {
      "risk": "风险",
      "passed": true,
      "evidence_refs": [],
      "notes": ""
    }
  ],
  "scope_notes": {
    "within_scope": true,
    "out_of_scope_touched": []
  },
  "blocked_items": [],
  "notes": []
}
```

`react_task_result.json` 必须包含 `task_id`、`verdict`、`pass`、`accepted`、`evidence`、`criteria_results`、`required_check_results`、`negative_check_results`、`risk_check_results`、`plan_validation_results`、`scope_compliance` 和 `required_follow_up`。

## Constraints

- 不得新增需求。
- 不得扩大当前 task 范围。
- 不得处理非当前 task。
- 不得把未执行检查或缺失证据伪装成通过。
- `act` 不得输出 pass/fail 验收结论，不得写 `.lgwf/react_task_result.json`。
- `observe` 不得修改被审查 artifact。
