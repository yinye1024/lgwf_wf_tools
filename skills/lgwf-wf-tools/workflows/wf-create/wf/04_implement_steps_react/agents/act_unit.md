# implement_steps_react act unit

## Role
这是单个 implementation unit 的历史落地约束文档。当前 `implement_one_unit.lgwf` 已改为确定性 `PY implement_current_unit` 节点，本文件保留为单元边界说明，不作为运行 prompt。

## Inputs
- `agents/spec.md`：本 ReAct 循环的共同准则，是路径、拓扑、DSL 和排除范围的权威约束。
- `.lgwf/current_implementation_unit_context.json`：当前 implementation unit 的完整上下文，包含 unit id、unit 类型、目标文件、目标目录、步骤设计摘要、实现 reason、observe 反馈和路径上下文。
- `state.lgwf_wf_create.current_implementation_unit_target_dirs`：当前脚本允许写入的目标目录集合。
- `state.lgwf_wf_create.current_implementation_unit_target_files`：当前脚本允许修改的目标文件集合。

## Mandatory First Step
先读取 `agents/spec.md`，再读取 `.lgwf/current_implementation_unit_context.json`。如果当前 unit context 与 `agents/spec.md` 冲突，以 `agents/spec.md` 为准。

## Task
1. 只处理当前 implementation unit，按 unit context 中的 `objective`、`target_files`、`target_dirs`、`step_designs` 和 `repair_focus` 执行最小实现或修复。
2. 如果 unit context 带有 observe 失败项，优先处理 `repair_focus` 中列出的失败，不扩大到其他 unit。
3. 需要参考设计时，优先使用 unit context 中的步骤摘要；只有确实需要补细节时，再读取目标文件或上下文中列出的只读资料。
4. 不修改 `current_implementation_unit_target_dirs` 之外的目录；如发现必须修改其他目录才能完成，应在输出 JSON 中记录 `blocked_reason`，不要擅自扩大范围。
5. 输出 unit 级结果，说明实际生成或修改的文件、跳过项、剩余风险和已处理的失败项。

## Output
由 `scripts/implement_current_unit.py` 写入 `.lgwf/current_implementation_unit_result.json`，内容为 UTF-8 JSON object。

## Output Format
至少包含：
- `unit_id`：当前 unit id。
- `status`：`ok`、`partial` 或 `failed`。
- `generated_files`：本 unit 实际生成或修改的目标 package 相对路径列表；可以是字符串或 `{ "path": "..." }` object。
- `generated`：可选，兼容汇总阶段的结构化生成摘要，例如 `root_files` 或 `by_step`。
- `handled_failures`：本 unit 已处理的 observe 失败项。
- `remaining_risks`：仍需后续处理的风险。
- `notes`：重要实现说明。

## Constraints
- 不得绕过 `agents/spec.md`。
- 不得改写其他 unit 的文件。
- 不得把未实际生成或修改的文件写入 `generated_files`。
- 不得运行全包修复、全包格式化或注册 facade 的命令。
