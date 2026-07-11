# collect-target-context

## step_slug

`collect-target-context`

## step_name

目标仓库上下文采集

## goal

为 `repo-context-pack-embedded-workflow` 的 `target_context_inventory` 阶段定义可实现、可审阅的 workflow 步骤设计，确保后续实现只在 `skills/repo-context-pack` 内生成 package 文件，并保持 `ws/.lgwf` 作为唯一运行状态边界。

## inputs

- 上游阶段或节点：
  - `target_context_inventory` 来源于已确认业务流。
- 依赖文件或状态：
  - `现有 `scripts/build_context_pack.py` 的遍历、跳过目录和文本候选规则`
  - `模块识别、命令提取、风险提取和阅读顺序生成的结构化输出需求`
  - `第一版重点支持普通 Python/Markdown 仓库、Codex skill 和 LGWF workflow package 的范围说明`
- 关键约束：
  - 遵守 `wf/` 唯一 workflow root。
  - 阶段目录必须是第一层 `wf/<stage>/`，不得创建孙级 workflow。
  - 运行状态只能写入 `ws/.lgwf`。

## outputs

- 扫描与采集步骤设计
- 结构化中间产物约定
- 与现有脚本复用或包装的接口说明

## dependencies

- entry_scope_resolution -> target_context_inventory：已解析的输入参数、目标目录/输出目录边界、跳过规则和扫描深度策略。
- target_context_inventory -> context_pack_rendering：入口文件、模块地图种子、命令候选、风险候选、推荐阅读顺序和扫描统计。

## implementation_suggestions

- 在目标 package 内为 `target_context_inventory` 准备 `wf/target_context_inventory/workflow.lgwf`。
- 若该阶段需要 prompt、脚本或资源，分别放入 `wf/target_context_inventory/agents/`、`wf/target_context_inventory/scripts/`、`wf/target_context_inventory/resources/`。
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
