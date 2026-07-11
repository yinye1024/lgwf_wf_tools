# confirm-verification-plan

## step_slug

`confirm-verification-plan`

## step_name

确认验证计划

## goal

设计 `wf/04_confirm_verification_plan/workflow.lgwf`，在进入耗时或写入型验证之前，用固定 `approve` / `revise` / `reject` 三分支 REVIEW 把验证计划固化下来。这个阶段的目标是确保维护者在执行前就能完整看到变更摘要、风险等级、待执行命令和写入目录，同时把 reject/修订闭环留在子 workflow 内部，不让父流程承担审批细节。

## inputs

- 上游阶段或节点：
  - `plan-verification`
  - `.lgwf/business_flow.json` 中 `04_confirm_verification_plan` 阶段定义
- 依赖文件或状态：
  - `.lgwf/verification_plan_proposal.json`
  - `.lgwf/change_context.json`
  - `.lgwf/impact_classification.json`
  - `.lgwf/create_reference_context/dsl-assist/create-workflow.md`
  - `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md`
- 关键约束：
  - 必须使用 `REVIEW`，不能退化为二元 `APPROVAL`
  - `approve` 后才允许固化 `.lgwf/verification_plan.json`
  - `revise` 必须提交完整修订计划
  - `reject` 必须在子 workflow 内 `FAIL_ALL`

## outputs

- 预期生成的文件：
  - `wf/04_confirm_verification_plan/workflow.lgwf`
  - `wf/04_confirm_verification_plan/scripts/*.py`
  - `wf/04_confirm_verification_plan/resources/*`
  - `.lgwf/verification_plan_approval.json`
  - `.lgwf/verification_plan.json`
- 预期生成的目录：
  - `wf/04_confirm_verification_plan/agents/`
  - `wf/04_confirm_verification_plan/scripts/`
  - `wf/04_confirm_verification_plan/resources/`
- 交付给下游的结构片段：
  - 可展示给维护者的 confirmation context
  - `approve` 后固化的确认计划
  - `revise` / `reject` 的显式 route 规则

## dependencies

- 前置步骤：
  - `plan-verification`
- 依赖节点：
  - REVIEW 展示模板
  - `verification_plan_proposal` 的命令、写入影响和范围估算
- 需要人工确认的位置：
  - 当前阶段本身就是唯一强制人工确认点

## implementation_suggestions

- 使用准备脚本把 `change_context`、`impact_classification` 和 `verification_plan_proposal` 聚合成一个 REVIEW context，对维护者展示变更摘要、风险等级、命令清单、写入目录、可选决策和提交格式。
- `approve` 路径只固化 proposal 内容，不让 REVIEW 返回值承担生成业务结构的责任；固化后的 `.lgwf/verification_plan.json` 应保持与 proposal 同形或稳定超集。
- `revise` 路径需要重新进入同一个 REVIEW 节点，允许维护者调整命令、timeout、skip 条件或 zip 输出路径，但不能借机新增未解释的额外业务目标。
- `reject` 直接在子 workflow 内终止，不把 reject route 抛给根 workflow 汇总节点。
- 资源目录中可以放 REVIEW 展示模板、decision JSON 示例和字段说明，避免 prompt 自行拼接不稳定文案。

## acceptance_notes

- 重点确认 REVIEW context 展示的是完整 plan JSON，而不是只展示摘要列表。
- 重点确认 `revise` 的提交值必须是完整对象，包含修订后的命令和评论，而不是仅提交局部 diff。
- 重点确认 reject 终止逻辑留在 `04_confirm_verification_plan` 子 workflow 内部，父 workflow 只看到成功完成或整体失败。

## out_of_scope

- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 在当前阶段实际执行任何验证命令
