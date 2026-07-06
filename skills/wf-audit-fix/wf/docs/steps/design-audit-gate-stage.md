# design-audit-gate-stage

## step_slug
`design-audit-gate-stage`

## step_name
真实目标目录 audit 闸门阶段设计

## goal
为 `real_audit_gate` 阶段设计首轮真实目录 audit 的执行与分流逻辑，确保 workflow 先对真实目标 package 做静态审核，再根据结果决定直接成功结束还是进入 candidate 修复循环。

## inputs
- `design-input-resolution-stage` 产出的 `runtime_context`、`normalized_target_workflow_lgwf`、`resolved_target_package_root` 和 `attempt_policy` 契约。
- `.lgwf/business_flow.json` 中 `real_audit_gate` 阶段的 `objective`、`key_nodes`、`outputs` 以及到 `candidate_repair_loop` / `result_summary` 的 handoff 说明。
- `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md` 中关于 `scripts/lgwf.py audit`、UTF-8 文件可读性、相对路径和 workflow/step 结构的检查要求。
- `04_confirm_business_flow/resources/scaffold_template_spec.md` 中“根 workflow 只编排阶段、阶段细节在第一层子 workflow 内完成”的边界。
- `prepare-package-layout` 输出的阶段目录映射，尤其是本阶段落在 `wf/04_confirm_business_flow/` 的约定。

## outputs
- `wf/04_confirm_business_flow/workflow.lgwf` 的设计草案，至少覆盖 `run_initial_real_audit`、`capture_initial_diagnostics`、`decide_exit_or_enter_candidate_loop` 节点。
- 本阶段脚本与资源清单草案，用于 audit 调用、stderr/stdout 采集、结构化诊断摘要和路由决策。
- 结构化输出契约，至少覆盖 `initial_audit_result`、`initial_audit_diagnostics`、`entry_decision`。
- 当首次真实目录 audit 已通过时，直接向 `result_summary` 交付终止依据的说明。

## dependencies
- 依赖 `design-input-resolution-stage` 已固定真实目标目录路径和尝试策略。
- 本阶段完成后，`design-candidate-repair-loop` 才能读取首轮失败诊断；若首轮 audit 已通过，则后续修复与 promote 阶段不应被执行。
- 不新增新的人工确认点；分支判断完全基于静态 audit 结果。

## implementation_suggestions
- 在 `wf/04_confirm_business_flow/workflow.lgwf` 内完成 audit 执行、诊断沉淀和分支路由，根 `wf/workflow.lgwf` 只引用本阶段子 workflow。
- 将 audit 结果统一整理成结构化对象，字段命名与后续 candidate 修复循环和 summary 阶段复用一致。
- 若需要保留人工可读说明，可在 `wf/04_confirm_business_flow/resources/` 预留摘要模板，但实际运行产物仍只落在 `ws/.lgwf` 或 `reports/`。
- 本阶段不得把 candidate 复制与修复逻辑混入自身节点，进入 candidate 循环前只负责首轮真实目录诊断。

## acceptance_notes
- 必须坚持“先真实目录 audit，再决定是否进入 candidate 修复”的顺序。
- 必须明确首次 audit 的目标是静态 DSL/audit 诊断，不是执行目标 workflow 业务逻辑。
- 必须保证本阶段输出足够支撑后续循环，不让下游再从原始 shell 输出重新猜字段。

## out_of_scope
- `lgwf-wf-prompt-fix` 集成。
- candidate 副本修复动作。
- promote 回真实目录。
- 端到端运行保证。
