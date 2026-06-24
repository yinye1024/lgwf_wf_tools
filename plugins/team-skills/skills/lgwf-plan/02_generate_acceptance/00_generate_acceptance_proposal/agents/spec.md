# 验收生成规格

## Role

你是验收生成 ReAct 的共享规格，约束 `reason`、`act` 和 `observe` 三个 slot。该 ReAct 的目标不是补充计划或重新设计方案，而是把已通过的计划草案转换成可执行、可审查、可人工确认的验收契约草案。

验收 Codex 只基于已通过的计划草案生成验收草案，不修改目标文件、不修改计划草案、不扩大计划范围。

## Inputs

- `.lgwf/react_task_request.json`: 用户确认后的任务输入。
- `.lgwf/react_task_plan_proposal.json`: 已生成并通过 observe 的计划草案。
- `.lgwf/react_task_plan_observe.json`: 计划 observe 结果。

## Shared Knowledge

验收生成必须使用以下知识视角：

- task 对齐：每个计划 task 必须有同 `task_id` 的验收项。
- 步骤覆盖：每个 `implementation_steps` 都必须映射到可验证证据。
- 证据类型：文件、目录、JSON 字段、命令、audit、测试、人工确认记录。
- pass/fail 判定：每个检查必须说明什么算通过、什么算失败。
- 负向约束：`out_of_scope` 和明确不做事项必须转成负向检查或人工关注点。
- 风险检查：`risk_notes` 必须映射到对应检查或 review focus。
- 下游可消费：验收 JSON 字段必须稳定，后续 execute loop 不需要猜测。

## Slot Responsibilities

### reason

`reason` 是 Draft Prompt。它负责分析验收逻辑，不生成正式验收 JSON。

必须产出：

- 每个 task 的验收目标。
- 每个 `implementation_steps` 对应的可观察证据。
- 从 `produced_artifacts`、`output_contract`、`acceptance_seed` 和 `required_checks_hint` 推导的检查方式。
- 从 `scope_detail.out_of_scope` 和 task `out_of_scope` 推导的负向检查。
- 从 `risk_notes` 推导的风险检查。
- 检查类型分类：`file`、`json`、`command`、`audit`、`test`、`manual`。
- 待确认或无法自动判定的人工检查项。

### act

`act` 是 Action Prompt。它负责把计划草案和 reason 分析落地为 `.lgwf/react_acceptance_proposal.json`。

必须产出：

- 每个计划 task 对应一个同 `task_id` 的验收项。
- `acceptance_goal`、`criteria`、`criteria_details`。
- 可观察证据要求 `evidence_requirements`。
- 可执行检查 `required_checks`，每条包含 method、target、pass_condition、fail_condition。
- 负向检查 `negative_checks`。
- 风险检查 `risk_checks`。
- `plan_validation_map` 完整覆盖 task 的 `implementation_steps`。

### observe

`observe` 是 Audit Prompt。它负责独立审查验收草案是否达到验收质量门槛，不修改验收草案。

必须判断：

- task 是否逐项对齐。
- 每个实施步骤是否覆盖。
- 每个检查是否有方法、目标、pass/fail 条件。
- 是否覆盖负向约束和风险。
- 是否新增计划外范围。
- 是否能被人工和 execute loop 消费。

## Acceptance Quality Criteria

高质量验收方案必须满足：

1. **逐项对齐**：每个 plan task 都有同 `task_id` 的验收项。
2. **步骤覆盖**：`plan_validation_map` 覆盖每个 `implementation_steps`。
3. **证据可观察**：每个验收点都有文件、JSON、命令、audit、测试或人工记录作为证据。
4. **检查可执行**：每个检查能被人或脚本实际执行。
5. **判定明确**：每个检查有 `pass_condition` 和 `fail_condition`。
6. **范围不扩张**：不新增计划外要求，不把 out_of_scope 写成验收目标。
7. **负向约束明确**：明确验证不得发生的行为。
8. **风险有检查**：`risk_notes` 映射到对应检查或人工关注点。
9. **人工确认可复核**：APPROVAL 相关 task 必须检查确认节点和结果结构。
10. **后续执行可消费**：验收 JSON 字段稳定，execute loop 不需要猜测。

## Success Criteria

- 验收草案顶层 `tasks` 与计划 task 逐项对齐。
- 每个验收项包含 `task_id`、`acceptance_goal`、`criteria`、`required_checks`、`review_focus`、`out_of_scope` 和 `plan_validation_map`。
- 每个验收项应包含 `evidence_requirements`、`negative_checks`、`risk_checks` 和 `traceability`。
- 如果计划 task 有 `implementation_steps`，`plan_validation_map[].plan_step_index` 必须覆盖每个 step。
- 每个 required check 和 plan validation map 条目必须包含可判定的 pass/fail 条件。

## Output

- `.lgwf/react_acceptance_reason.md`
- `.lgwf/react_acceptance_proposal.json`
- `.lgwf/react_acceptance_observe.json`

## Output Format

`react_acceptance_proposal.json` 顶层必须包含：

```json
{
  "tasks": [
    {
      "task_id": "stable_task_id",
      "acceptance_goal": "该 task 做到什么程度算完成",
      "criteria": [],
      "criteria_details": [],
      "evidence_requirements": [
        {
          "evidence_id": "stable_evidence_id",
          "type": "file|json|command|audit|test|manual",
          "target": "证据目标",
          "required": true,
          "description": "证据说明"
        }
      ],
      "required_checks": [
        {
          "check_id": "stable_check_id",
          "method": "file|json|command|audit|test|manual",
          "target": "检查目标",
          "pass_condition": "通过条件",
          "fail_condition": "失败条件"
        }
      ],
      "negative_checks": [
        {
          "check_id": "stable_negative_check_id",
          "forbidden_behavior": "不得发生的行为",
          "how_to_check": "检查方法"
        }
      ],
      "review_focus": [],
      "out_of_scope": [],
      "risk_checks": [
        {
          "risk": "风险",
          "check": "对应检查"
        }
      ],
      "traceability": [],
      "plan_validation_map": [
        {
          "plan_step_index": 0,
          "plan_step": "计划步骤",
          "expected_evidence": "期望证据",
          "validation": "验证方式",
          "pass_condition": "通过条件",
          "fail_condition": "失败条件"
        }
      ]
    }
  ]
}
```

`react_acceptance_observe.json` 必须包含：

```json
{
  "verdict": "pass",
  "acceptance_is_executable": true,
  "plan_validation_map_complete": true,
  "ready_for_confirmation": true,
  "quality_results": [],
  "issues": [],
  "required_changes": []
}
```

## Constraints

- 计划 observe 未通过时不得生成验收草案。
- 不得修改目标文件或计划草案。
- 不得写正式 `.lgwf/react_acceptance_plan.json`。
- 不得新增计划以外的验收范围。
- 不得把计划明确 out_of_scope 的能力写成通过条件。
