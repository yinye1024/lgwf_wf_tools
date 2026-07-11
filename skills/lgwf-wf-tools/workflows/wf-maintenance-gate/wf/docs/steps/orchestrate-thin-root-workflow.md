# orchestrate-thin-root-workflow

## step_slug

`orchestrate-thin-root-workflow`

## step_name

根 workflow 薄编排与 artifact contract

## goal

定义 `wf/workflow.lgwf` 和 `wf/artifact_contracts.json` 的控制面边界，让根 workflow 只表达六个第一层子 workflow 的顺序与最终产物契约，不承载任何阶段私有脚本、prompt、人工确认实现细节或业务判断。这个步骤的作用是把“顶层编排”和“阶段内部逻辑”彻底分离，使 authoring audit、resume 和后续诊断都围绕稳定的一层目录开展。

## inputs

- 上游阶段或节点：
  - `.lgwf/business_flow.json` 中的 `stages`、`stage_dependencies` 和 `downstream_step_inputs`
- 依赖文件或状态：
  - `.lgwf/create_reference_context/dsl-assist/create-workflow.md`
  - `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md`
  - `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md`
  - `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`
  - `docs_tmp/wf-maintenance-gate-development.md`
- 关键约束：
  - 根入口固定为 `wf/workflow.lgwf`
  - 根 workflow 只能引用第一层 `wf/<stage>/workflow.lgwf`
  - `wf/artifact_contracts.json` 必须声明关键 `.lgwf` 产物和报告
  - 子 workflow 的 `approve` / `revise` / `reject` 细节不得泄露给父 workflow

## outputs

- 预期生成的文件：
  - `wf/workflow.lgwf`
  - `wf/artifact_contracts.json`
- 预期生成的目录：
  - 只引用已确认的第一层阶段目录，不新增孙级 workflow
- 交付给下游的结构片段：
  - 根流程顺序：`01_collect_change_context -> 02_classify_impact -> 03_plan_verification -> 04_confirm_verification_plan -> 05_run_verification -> 06_summarize_gate_result`
  - 关键 artifact 声明：`.lgwf/change_context.json`、`.lgwf/impact_classification.json`、`.lgwf/verification_plan_proposal.json`、`.lgwf/verification_plan.json`、`.lgwf/verification_results.json`、`.lgwf/failure_routes.json`、`.lgwf/maintenance_gate_summary.json`、`ws/reports/wf-maintenance-gate/report.md`

## dependencies

- 前置步骤：
  - `define-package-contracts`
  - `define-shared-helper-and-tests`
  - `collect-change-context`
  - `classify-impact`
  - `plan-verification`
  - `confirm-verification-plan`
  - `run-verification`
  - `summarize-gate-result`
- 依赖节点：
  - 六个已确认业务阶段的 handoff 语义
- 需要人工确认的位置：
  - 当前步骤本身不新增人工确认；`04_confirm_verification_plan` 的 REVIEW 和其 `reject -> FAIL_ALL` 闭环必须留在子 workflow 内部

## implementation_suggestions

- 根 `wf/workflow.lgwf` 使用 `ENTRY FLOW main` 和命名 `FLOW main` 表达主流程，不在根文件里声明阶段私有 `PY`、`CODEX`、`REVIEW`、`ROUTE` 细节。
- 六个阶段目录名直接使用已确认业务流的 `stage_id`：`01_collect_change_context`、`02_classify_impact`、`03_plan_verification`、`04_confirm_verification_plan`、`05_run_verification`、`06_summarize_gate_result`。
- `04_confirm_verification_plan` 作为子 workflow 自己处理 `approve` / `revise` / `reject`。父 workflow 只在子 workflow 成功完成后继续到 `05_run_verification`，不承担 reject 汇总分支。
- 在 `wf/artifact_contracts.json` 中同时声明机器可读产物与面向人的报告路径，避免后续阶段通过未声明的 `.lgwf` 临时文件做隐式通信。
- 所有 workflow 引用都使用包内相对路径，禁止绝对路径、盘符路径和 `..`。

## acceptance_notes

- 重点确认根 workflow 保持薄编排，不直接处理审批 route、stdout 摘要、失败分类或 Markdown 报告渲染。
- 重点确认没有 `wf/<stage>/<substage>/workflow.lgwf`，也没有把阶段节点重新堆回根 `workflow.lgwf`。
- 重点确认 `wf/artifact_contracts.json` 中声明的产物与 `AGENTS.md`、`README.md`、`entry_contract.json` 中描述一致。
- 若后续实现发现需要跨阶段传递额外字段，应优先把它们纳入已声明 artifact，而不是让父 workflow 读取子 workflow 的内部临时文件。

## out_of_scope

- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 在根 workflow 中直接实现任何阶段私有脚本、prompt 或审批文案
