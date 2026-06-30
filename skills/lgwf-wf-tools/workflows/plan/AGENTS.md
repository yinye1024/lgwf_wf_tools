# plan 工作流指引

本目录是 `lgwf-wf-tools` 内部的计划驱动 workflow package，不是独立 Codex skill。它用于把复杂任务拆成可确认的计划契约、验收契约，并在用户确认后按 ReAct 闭环执行。

facade 必须从根目录 `registry.json` 派发本 workflow，使用内置 `vendor/lgwf-client-assist/scripts/lgwf.py` 启动或继续运行；不得要求用户激活外部 `lgwf-plan` 或 `lgwf-client-assist` skill。

## 适用场景

- 用户明确要求“先规划再执行”“先给验收标准”“确认计划后再改文件”。
- 任务跨多个文件、多个阶段或多个验证步骤，直接执行容易丢失目标边界。
- 需要把实现计划、验收方案和执行记录沉淀为 LGWF 产物。

不适用场景：

- 目标是修复已有 workflow 的真实运行失败，优先回到 facade 路由 `wf-fix`。
- 目标只是 prompt 基础规范修复或 prompt 设计升级，优先回到 `wf-prompt-fix` 或 `wf-prompt-upgrade`。
- 目标只是为已有 workflow 生成 E2E 测试，优先回到 `e2e-test-generator`。

## 约束

- 主智能体只收集输入、展示草案、提交用户确认和继续执行，不直接替代独立 Codex 生成计划或验收。
- `wf/workflow.lgwf` 是入口；`wf/` 是唯一 workflow package root。
- work-dir 使用同级固定目录 `ws/`，不要放进 `wf/` 内部。
- `prompt_ref`、`script_ref` 必须通过 node config 传递给 client；runtime 不读取这些文件内容。
- 计划 observe 通过前不得生成验收；验收 observe 通过前不得请求用户确认。
- 用户 approve 前不得写正式 `.lgwf/react_task_plan.json` 或 `.lgwf/react_acceptance_plan.json`。
- 执行 observe 只能按已确认验收方案评审，不得新增需求。

## 输入契约

facade 应尽量提供结构化 `react_task_request`。最小形态：

```json
{
  "react_task_request": {
    "objective": "要完成的复杂任务目标",
    "target_type": "modify_artifact",
    "analysis_target_files": ["D:/example/path/to/file.md"],
    "constraints": ["先生成计划和验收契约，用户确认后再修改目标文件"]
  }
}
```

`target_type` 必须是 `create_artifact`、`modify_artifact`、`execute_process`、`analyze`、`fix` 或 `review` 之一。用户没有给出足够信息时，facade 先主动确认目标、范围、可修改文件、验收口径和是否允许真实执行。

## Approval 边界

- `collect_react_task_request` 用于确认原始任务输入；facade 只能提交用户确认后的目标和约束。
- `confirm_plan_and_acceptance` 用于确认计划契约和验收契约；用户 approve 前不得执行实现 task。
- 执行阶段遇到最大轮次人工决策时，facade 必须展示当前 task、失败证据、可选分支和风险，再提交用户明确选择。

## 固定产物

- `.lgwf/react_task_request.json`
- `.lgwf/react_task_plan_proposal.json`
- `.lgwf/react_acceptance_proposal.json`
- `.lgwf/react_task_plan.json`
- `.lgwf/react_acceptance_plan.json`
- `.lgwf/react_task_context.json`
- `.lgwf/react_task_result.json`
- `.lgwf/react_task_history.json`
- `reports/react-task/react_task_report.md`

## 最小验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\plan\tests
```
