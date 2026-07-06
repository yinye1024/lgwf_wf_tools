# design-candidate-repair-loop

## step_slug
`design-candidate-repair-loop`

## step_name
Candidate 修复与复检循环阶段设计

## goal
为 `candidate_repair_loop` 阶段设计受预算约束的诊断、修复、再审计闭环，使 workflow 只在隔离 candidate 副本上修改文件，并在 audit 通过后交付可 promote 的快照。

## inputs
- `design-audit-gate-stage` 输出的 `initial_audit_diagnostics`、`entry_decision` 和 candidate 循环入口条件。
- `.lgwf/business_flow.json` 中 `candidate_repair_loop` 阶段的 `objective`、`key_nodes`、`outputs` 和到 `promote_and_reaudit` / `result_summary` 的 handoff。
- `.lgwf/create_requirements.json` 中已确认的 `max_attempts` 默认值与“只修静态 DSL/audit 问题”的范围限制。
- `.lgwf/create_reference_context/dsl-assist/create-workflow.md` 与 `workflow-audit-checklist.md` 中关于 REACT、AGENT_LOOP、子 workflow 自包含和 `VERIFY` / `DECIDE` 契约的规则。
- `04_confirm_business_flow/resources/scaffold_template_spec.md` 中关于阶段私有 prompt、脚本和资源留在 `wf/<stage>/`、禁止孙级 workflow 的规范。

## outputs
- `wf/07_confirm_step_designs/workflow.lgwf` 的循环设计草案，明确选择 REACT 或 AGENT_LOOP，并列出诊断、计划、修改、验证、决策节点职责。
- 本阶段所需 `agents/*.md`、`scripts/*.py`、`resources/*.md` 的占位清单，覆盖 candidate 复制、诊断记录、修复执行、再审计和终止判定。
- 结构化输出契约，至少覆盖 `candidate_attempt_log`、`latest_candidate_audit_result`、`candidate_pass_snapshot`、`loop_exit_reason`。
- 对下游 `promote_and_reaudit` 的通过快照交付说明，以及达到最大尝试次数时直接进入 summary 失败分支的说明。

## dependencies
- 依赖 `design-audit-gate-stage` 已提供首轮真实目录失败诊断或明确的进入循环判定。
- 本阶段未得到 `candidate_pass_snapshot` 前，不得进入 promote 阶段。
- 达到最大尝试次数或出现不可恢复诊断时，应直接形成失败终止信息，供 summary 阶段消费。

## implementation_suggestions
- 若使用 `AGENT_LOOP`，严格遵守 `OBSERVE`、`DIAGNOSE`、`PLAN`、`ACT`、`VERIFY`、`DECIDE` 六个必填 slot；`VERIFY` 输出必须包含 `passed`，`DECIDE` 输出必须包含 `category` 和 `reason`。
- 若使用 `REACT`，需明确 `DECIDE` 如何输出继续或退出，并用脚本节点稳定维护尝试次数和循环预算。
- 所有写操作只允许落在 candidate 副本，真实目标目录在本阶段必须保持只读。
- 阶段私有 prompt、脚本和诊断模板均放在 `wf/07_confirm_step_designs/`，不通过孙级 workflow 再拆目录。

## acceptance_notes
- 必须明确 candidate 副本是唯一修复对象，真实目标目录 promote 必须推迟到下游独立阶段。
- 必须写清循环预算、停止条件和失败出口，避免无界重试。
- 必须让结构化输出能够直接支撑下游 promote 或 summary，不要求实现阶段再反解析自由文本。

## out_of_scope
- `lgwf-wf-prompt-fix` 集成。
- `lgwf-wf-tools` facade 接入实现。
- 对真实目标目录的回写。
- 目标 workflow 端到端运行保证。
