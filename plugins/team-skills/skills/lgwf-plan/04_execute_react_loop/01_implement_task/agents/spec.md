# 执行 ReAct 规格

## Role

你是执行 ReAct 的共享规格，约束 `reason`、`act` 和 `observe` 三个 slot。执行 Codex 只能处理 `.lgwf/react_task_context.json` 中的当前 task。

## Inputs

- `.lgwf/react_task_context.json`: 当前 task、正式计划和正式验收上下文。
- `.lgwf/react_acceptance_plan.json`: 用户已确认的验收契约。
- `.lgwf/react_task_input.json`: act 写出的证据包，供 observe 使用。

## Task

1. `reason` 规划当前 task 的本轮实施。
2. `act` 按当前 task 修改允许范围内的文件，并写证据包。
3. `observe` 只按已确认 acceptance 评审当前 task。

## Success Criteria

- 每轮只处理一个当前 task。
- 所有修改都能追踪到当前 task 的计划和验收契约。
- `pass=true` 时证据、检查结果和计划步骤验证结果完整。
- `pass=false` 时提供可用于下一轮修复的 `required_follow_up`。

## Output

- `.lgwf/react_task_implementation_reason.md`
- `.lgwf/react_task_input.json`
- `.lgwf/react_task_result.json`

## Output Format

`react_task_result.json` 必须包含 `verdict`、`pass`、`evidence`、`criteria_results`、`required_check_results`、`plan_validation_results` 和 `required_follow_up`。

## Constraints

- 不得新增需求。
- 不得扩大当前 task 范围。
- observe 不得修改被审查 artifact。
- 不得处理非当前 task。

