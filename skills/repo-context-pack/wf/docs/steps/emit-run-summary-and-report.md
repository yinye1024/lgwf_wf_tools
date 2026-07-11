# emit-run-summary-and-report

## step_slug

`emit-run-summary-and-report`

## step_name

运行摘要与交接收尾

## goal

为 `repo-context-pack-embedded-workflow` 的 `workflow_summary_handoff` 阶段定义可实现、可审阅的 workflow 步骤设计，确保后续实现只在 `skills/repo-context-pack` 内生成 package 文件，并保持 `ws/.lgwf` 作为唯一运行状态边界。

## inputs

- 上游阶段或节点：
  - `workflow_summary_handoff` 来源于已确认业务流。
- 依赖文件或状态：
  - ``output_dir/summary.json` 与 workflow 本地摘要之间的关联关系`
  - ``ws/.lgwf/repo_context_pack_summary.json` 和 `ws/reports/repo-context-pack/report.md` 的新增产物要求`
  - `上层 skill 或后续 agent 需要消费的完成态 payload`
- 关键约束：
  - 遵守 `wf/` 唯一 workflow root。
  - 阶段目录必须是第一层 `wf/<stage>/`，不得创建孙级 workflow。
  - 运行状态只能写入 `ws/.lgwf`。

## outputs

- 运行摘要步骤设计
- workflow 报告模板要求
- 最终完成态输出契约

## dependencies

- context_pack_rendering -> workflow_summary_handoff：固定上下文包产物路径、产物摘要、运行统计和需要写入 workflow 本地状态的完成信息。

## implementation_suggestions

- 在目标 package 内为 `workflow_summary_handoff` 准备 `wf/workflow_summary_handoff/workflow.lgwf`。
- 若该阶段需要 prompt、脚本或资源，分别放入 `wf/workflow_summary_handoff/agents/`、`wf/workflow_summary_handoff/scripts/`、`wf/workflow_summary_handoff/resources/`。
- 根 `wf/workflow.lgwf` 只编排第一层子 workflow，不承载阶段内部细节。
- 复用现有脚本能力时，先用 wrapper 固化输入输出契约，不把运行态文件写入源码根目录。

## acceptance_notes

- 人工确认时重点核对 step_slug、stage_id、输出文件和只读/写入边界是否与已确认业务流一致。
- 如果 `target_dir` 位于只读位置，输出目录策略必须在实现脚本中显式失败或回退，并写入摘要。
- 如果 `max_files` 或 `depth` 导致扫描截断，摘要和报告必须记录截断事实。

## out_of_scope

- `lgwf-wf-prompt-fix` 集成
- `lgwf-wf-tools` registry 自动注册
- 自动修复、自动发布或端到端运行保证
