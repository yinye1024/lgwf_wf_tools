# execute-batch-audit

## step_slug
`execute-batch-audit`

## step_name
批量审计执行阶段设计

## goal
设计 `batch_audit` 第一层子 workflow，使其只对授权清单中的 `workflow.lgwf` 执行静态 audit，并稳定产出可供分类阶段消费的诊断结果与统计信息。

## inputs
- `prepare-target-manifest` 提供的 `target_manifest.json`、路径合法性校验结果和授权边界说明。
- `.lgwf/business_flow.json` 中 `batch_audit` 阶段的 `objective`、`key_nodes`、`outputs` 和对 `classify_findings` 的 handoff。
- `.lgwf/create_requirements.json` 中“不运行业务 workflow、只做静态 audit”的需求边界。
- `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md` 中关于 authoring audit、资源引用和最小可验收结构的规则。
- `scaffold_template_spec.md` 中关于子 workflow 自包含、阶段私有 `agents/`、`scripts/`、`resources/` 目录布局的要求。

## outputs
- `wf/02_batch_audit/workflow.lgwf` 的阶段设计草案，至少覆盖 `prepare_audit_jobs`、`run_target_audit`、`collect_audit_diagnostics` 和 `summarize_audit_counts`。
- `batch_audit_result.json` 与 `batch_audit_stats.json` 的结构约束，明确每个目标的 audit 状态、diagnostics、失败摘要和总量统计。
- 本阶段私有脚本与资源草案，例如 audit 执行封装、diagnostic 归一化和失败摘要模板。
- 向下游 `classify-diagnostics` 交接的字段说明，明确 diagnostics、目标标识、来源模式和错误摘要如何稳定输出。

## dependencies
- 依赖 `prepare-target-manifest` 产出的授权清单，不能自行重新发现目标。
- 下游 `classify-diagnostics` 依赖本阶段输出的标准化 diagnostics；字段命名和空结果处理策略必须稳定。
- 本阶段不引入人工确认，业务审批仍由后续 `prepare-upgrade-plan-approval` 统一承担。

## implementation_suggestions
- 将本阶段所有节点收敛到 `wf/02_batch_audit/workflow.lgwf`，由父 workflow 只做阶段编排。
- 优先使用脚本节点调用 bundled client 的 `lgwf.py audit`，把原始输出归一化为统一 JSON 结构，再写入阶段产物。
- 设计“单目标失败不终止整体批处理”的收集策略，把不可审计目标记录为失败项而不是让整个阶段崩溃。
- 在 `resources/` 中补充 diagnostics 字段说明，帮助后续分类与人审上下文复用同一数据结构。

## acceptance_notes
- 必须明确本阶段只执行静态 authoring audit，不运行目标 workflow，也不做任何写回修复。
- 必须说明当单个目标 audit 失败时，如何继续处理其他目标并在结果中保留失败摘要。
- 必须确认 `batch_audit_result.json` 与 `batch_audit_stats.json` 字段可直接供分类、计划和报告阶段复用，避免后续重复解析原始命令输出。

## out_of_scope
- 诊断分类规则制定。
- 自动修复或自由形式修改。
- 目标 workflow 的运行时验证。
- 端到端成功保证。
