# render-context-pack-artifacts

## step_slug

`render-context-pack-artifacts`

## step_name

上下文包产物生成

## goal

为 `repo-context-pack-embedded-workflow` 的 `context_pack_rendering` 阶段定义可实现、可审阅的 workflow 步骤设计，确保后续实现只在 `skills/repo-context-pack` 内生成 package 文件，并保持 `ws/.lgwf` 作为唯一运行状态边界。

## inputs

- 上游阶段或节点：
  - `context_pack_rendering` 来源于已确认业务流。
- 依赖文件或状态：
  - `固定输出产物集合`
  - `Markdown 与 JSON 必须 UTF-8 no BOM 的编码要求`
  - ``repo_context_pack.md`、`agent_handoff.md`、`module_map.json`、`command_inventory.json`、`risk_register.md`、`read_order.md` 的职责划分`
- 关键约束：
  - 遵守 `wf/` 唯一 workflow root。
  - 阶段目录必须是第一层 `wf/<stage>/`，不得创建孙级 workflow。
  - 运行状态只能写入 `ws/.lgwf`。

## outputs

- 产物渲染步骤设计
- 产物写入顺序与覆盖策略
- 产物完整性检查约定

## dependencies

- target_context_inventory -> context_pack_rendering：入口文件、模块地图种子、命令候选、风险候选、推荐阅读顺序和扫描统计。
- context_pack_rendering -> workflow_summary_handoff：固定上下文包产物路径、产物摘要、运行统计和需要写入 workflow 本地状态的完成信息。

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
