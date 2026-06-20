---
name: lgwf-plan
description: 通过 LGWF 计划、验收、用户确认和 ReAct 执行闭环处理复杂任务。
---

# lgwf-plan

当用户要求先规划、再确认验收、最后按验收闭环执行任务时使用本 skill。

## 使用方式

1. 进入本 skill 目录。
2. 使用相对 work-dir：`.tmp/<run-name>`。
3. 通过 `lgwf-client-assist` facade 运行 `workflow.lgwf`。
4. 在 `collect_react_task_request` 审批节点里按模板提交任务输入。
5. 在 `confirm_plan_and_acceptance` 审批节点里只回复 `approve` 或 `reject`，并可附修改意见。

主智能体不得绕过计划草案、验收草案或用户确认直接修改目标文件。

