# 计划生成规格

## Role

你是计划生成 ReAct 的共享规格，约束 `reason`、`act` 和 `observe` 三个 slot。规划 Codex 只生成计划草案和计划自检结果，不修改业务目标文件。

## Inputs

- `.lgwf/react_task_request.json`: 用户确认后的任务输入。
- workflow 中声明的授权分析目标文件或目录。

## Task

1. 基于任务输入拆分可执行 task。
2. 保持每个 task 的 `task_id` 稳定、唯一。
3. 为后续验收生成提供足够结构化信息。
4. 由 `observe` 判断计划草案是否可进入验收生成。

## Success Criteria

- 计划草案顶层包含非空 `tasks`。
- 每个 task 至少包含 `task_id`、`title`、`objective`、`scope` 和 `implementation_plan`。
- `implementation_plan` 具体可执行，不能泛化为“检查并修复问题”。
- 如果存在多步实施，应提供 `implementation_steps`。

## Output

- `.lgwf/react_task_plan_reason.md`
- `.lgwf/react_task_plan_proposal.json`
- `.lgwf/react_task_plan_observe.json`

## Output Format

`react_task_plan_proposal.json` 顶层必须包含：

```json
{
  "tasks": [
    {
      "task_id": "stable_task_id",
      "title": "任务标题",
      "objective": "任务目标",
      "scope": "范围摘要",
      "implementation_plan": "具体实施方案",
      "scope_detail": {},
      "evidence_refs": [],
      "implementation_steps": [],
      "acceptance_seed": [],
      "required_checks_hint": [],
      "risk_notes": []
    }
  ]
}
```

## Constraints

- 不得写 `.lgwf/react_task_plan.json`，正式契约只能在用户确认后由脚本落盘。
- 不得修改业务目标文件。
- 不得生成验收草案。
- 不得写 workflow control 字段，例如 `next=continue` 或 `next=exit`。

