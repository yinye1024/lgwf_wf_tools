# target_context_inventory 阶段提示

## 角色定位

本阶段负责把上一阶段已归一化的目标范围转成确定性的上下文盘点结果。运行时事实来源必须是 Python 脚本和输入 artifact，不得改成由 Codex 在执行时重新扫描目标仓库。

## 输入

- `state.repo_context_pack_request`：上一阶段归一化后的请求对象。
- 上一阶段会把请求 artifact 固化为 `.lgwf/repo_context_pack_request.json`，用于跨阶段命名一致性；本阶段实现以内存 state 为直接输入，避免把 package 级 artifact 边界硬编码成子 workflow 的外部依赖。

## 输出

- 工作区文件 `.lgwf/context_inventory.json`
- 运行时 state `repo_context_pack.context_inventory`
- 运行时 state `repo_context_pack.context_inventory_verification`

## 必须覆盖的信息

- 目标目录和目标文件的存在性、归属与扫描边界
- 递归清点得到的文件概览、模块信号和候选入口
- 从文本资料中提取的命令、测试命令、风险标记和截断信息
- 明确说明哪些内容只被记录为上下文，不会在本阶段执行

## 约束

- 只做确定性 Python 扫描，不调用运行时 Codex prompt 去分析目标资料。
- 不执行提取出的命令、测试命令、修复步骤或 TODO。
- 不改写目标范围，不扩展到请求之外的目录和文件。
- 输出路径固定使用 `.lgwf/context_inventory.json`，且内容需为 UTF-8 JSON object。
