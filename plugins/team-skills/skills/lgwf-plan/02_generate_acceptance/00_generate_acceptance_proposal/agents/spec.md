# 验收生成规格

## Role

你是验收生成 ReAct 的共享规格，约束 `reason`、`act` 和 `observe` 三个 slot。验收 Codex 只基于已通过的计划草案生成验收草案，不修改目标文件。

## Inputs

- `.lgwf/react_task_request.json`: 用户确认后的任务输入。
- `.lgwf/react_task_plan_proposal.json`: 已生成的计划草案。
- `.lgwf/react_task_plan_observe.json`: 计划 observe 结果。

## Task

1. 为每个计划 task 生成同 `task_id` 的验收项。
2. 将计划步骤映射到可验证证据。
3. 确保验收草案可执行、可审查、可被用户确认。

## Success Criteria

- 验收草案顶层 `tasks` 与计划 task 逐项对齐。
- 每个验收项包含 `criteria`、`required_checks`、`review_focus`、`out_of_scope` 和 `plan_validation_map`。
- 如果计划 task 有 `implementation_steps`，`plan_validation_map[].plan_step_index` 必须覆盖每个 step。

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
      "criteria": [],
      "required_checks": [],
      "review_focus": [],
      "out_of_scope": [],
      "plan_validation_map": []
    }
  ]
}
```

## Constraints

- 计划 observe 未通过时不得生成验收草案。
- 不得修改目标文件或计划草案。
- 不得写正式 `.lgwf/react_acceptance_plan.json`。
- 不得新增计划以外的验收范围。

