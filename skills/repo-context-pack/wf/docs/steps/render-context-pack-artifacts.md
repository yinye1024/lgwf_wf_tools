# render-context-pack-artifacts

## step_slug

`render-context-pack-artifacts`

## step_name

上下文包渲染

## goal

为 `repo-context-pack` 的 `context_pack_rendering` 阶段定义可实现、可审阅的 workflow 步骤设计，确保后续实现只在 `skills/repo-context-pack` 内生成 package 文件，并保持 `ws/.lgwf` 作为唯一运行状态边界。

## inputs

- 上游阶段或节点：
  - `context_pack_rendering` 来源于已确认业务流。
- 依赖文件或状态：
  - `structure_inventory`
  - `command_candidates`
  - `key_file_notes`
  - `risk_findings`
  - `read_order_candidates`
  - `固定产物清单`
- 关键约束：
  - 遵守 `wf/` 唯一 workflow root。
  - 阶段目录必须是第一层 `wf/<stage>/`，不得创建孙级 workflow。
  - 运行状态只能写入 `ws/.lgwf`。

## outputs

- repo_context_pack.md
- agent_handoff.md
- module_map.json
- command_inventory.json
- risk_register.md
- read_order.md
- summary.json

## dependencies

- target_context_inventory -> context_pack_rendering：结构映射、命令入口、关键文件、阅读顺序候选、风险与未知项等结构化盘点结果。
- context_pack_rendering -> workflow_summary_handoff：已渲染的 Markdown/JSON 交付物集合，以及各产物之间的覆盖范围、重点和风险一致性检查结果。

## implementation_suggestions

- 在目标 package 内为 `context_pack_rendering` 准备 `wf/context_pack_rendering/workflow.lgwf`。
- 若该阶段需要 prompt、脚本或资源，分别放入 `wf/context_pack_rendering/agents/`、`wf/context_pack_rendering/scripts/`、`wf/context_pack_rendering/resources/`。
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
