# design-promote-and-verify-stage

## step_slug
`design-promote-and-verify-stage`

## step_name
Promote 与真实目录复检阶段设计

## goal
为 `promote_and_reaudit` 阶段设计“candidate 通过后才允许回写真实目标目录，并立即重新 audit”的强约束流程，确保最终成功结论基于真实目录复检而非 candidate 中间状态。

## inputs
- `design-candidate-repair-loop` 输出的 `candidate_pass_snapshot`、`candidate_attempt_log` 或失败终止信息。
- `.lgwf/business_flow.json` 中 `promote_and_reaudit` 阶段的 `objective`、`key_nodes`、`outputs` 和到 `result_summary` 的 handoff。
- `design-input-resolution-stage` 输出的 `resolved_target_package_root` 与允许修改边界说明。
- `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md` 中关于相对路径、workflow audit 和 package 边界的检查要求。
- `04_confirm_business_flow/resources/scaffold_template_spec.md` 中关于阶段自包含和 `ws/.lgwf` 状态边界的约束。

## outputs
- `wf/09_summarize_create_result/workflow.lgwf` 中 promote 与真实目录复检部分的设计草案，至少覆盖 `promote_candidate_to_target`、`run_post_promote_real_audit`、`decide_success_or_fail`。
- 本阶段所需脚本与资源占位清单，覆盖 promote 前边界校验、目录回写、复检 audit 和失败摘要。
- 结构化输出契约，至少覆盖 `promote_result`、`post_promote_real_audit_result`、`final_status_candidate_or_target`、`final_diagnostics`。
- 当 candidate 未通过或 promote 不可执行时，直接向 summary 交付失败状态的说明。

## dependencies
- 依赖 `design-candidate-repair-loop` 已明确给出通过快照或失败终止原因。
- promote 前必须再次使用受控边界校验，确保写入对象仍是允许修改的真实目标 package。
- 本阶段完成后，`design-summary-stage` 才能基于真实目录最终状态输出摘要。

## implementation_suggestions
- 将 promote 与复检逻辑保留在 `wf/09_summarize_create_result/workflow.lgwf` 内，不新增孙级 workflow。
- promote 脚本应显式校验真实目录和 candidate 目录映射关系，防止 stale 路径或越界覆盖。
- 真实目录复检应尽量复用首轮 audit 相同的调用与摘要结构，减少 summary 阶段做兼容转换。
- 如备份、回滚或原子性策略尚未确认，可在资源说明中保留待确认项，但不要臆造确定实现。

## acceptance_notes
- 必须坚持“先 candidate audit 通过，再 promote，再真实目录复检”的固定顺序。
- 必须说明真实目录复检是强制步骤，不能用 candidate 通过结果替代。
- 若 promote 失败或复检失败，应输出失败终局，不得继续隐式重试或伪装为成功。

## out_of_scope
- `lgwf-wf-prompt-fix` 集成。
- `lgwf-wf-tools` facade 自动注册。
- 自动回滚、自动重试和端到端运行保证。
- 非静态 audit 范围之外的治理动作。
