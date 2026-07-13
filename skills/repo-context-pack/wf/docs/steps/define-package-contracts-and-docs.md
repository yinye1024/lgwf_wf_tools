# 定义 package 契约与入口文档

## 步骤标识

- `step_slug`: `define-package-contracts-and-docs`
- 对齐阶段：`01_entry_scope_resolution`、`04_workflow_summary_handoff`

## 目标

为 `skills/repo-context-pack` 固化根契约文档与入口说明，明确这是一个 `internal_workflow_package`，其真实 workflow 入口固定为 `wf/workflow.lgwf`，运行状态只允许写入 `ws/.lgwf/`。

## 输入

- `scaffold_plan.package_profile=internal_workflow_package`
- `scaffold_plan.target_package_root=skills/repo-context-pack`
- 入口请求中的 `target_dir`、`output_dir`、截断参数与只读边界要求
- 汇总阶段需要回写的固定状态文件名和通过标准

## 输出

- `AGENTS.md`：说明模块定位、边界、最小验证和禁止事项
- `README.md`：说明用途、输入输出、目录结构、运行方式和产物
- `entry_contract.json`：定义必填字段、默认值、失败规则和写入边界

## 确认要点

- 目录和根文件结构以 `internal_workflow_package` 为准，本轮不生成根 `SKILL.md`
- `entry_contract.json` 需要显式声明非法输入失败规则，以及 `target_dir` 只读、`output_dir` 可写、`ws/.lgwf/` 为唯一状态边界
- `README.md` 和 `AGENTS.md` 需要用中文说明固定产物、阶段顺序、最小验证和禁止事项

## 实现建议

- 将 `target_dir` 定义为只读扫描源，不在 workflow 运行时执行其中记录的命令、TODO 或修复步骤
- 将 `output_dir` 定义为上下文包产物目录，只允许写固定七个产物及其索引信息
- 在 `entry_contract.json` 中声明默认扫描参数、非法路径处理、缺失入口时的失败行为和 JSON UTF-8 要求
- 在根文档中同步记录当前输入漂移：已批准步骤曾提到 `skill_wrapped_workflow`，但结构事实源要求 `internal_workflow_package`

## 验收

- `AGENTS.md`、`README.md`、`entry_contract.json` 与本步骤文档的中文说明一致
- 根目录不生成 `workflow.lgwf`，唯一 workflow 根保持为 `wf/workflow.lgwf`
- 根目录不生成 `.lgwf`，运行状态边界仍为 `ws/.lgwf/`

## 禁止事项

- 不要在 `internal_workflow_package` 模式下创建根 `SKILL.md`
- 不要在根文档里承诺运行时 Codex 扫描目标仓库
- 不要把 `output_dir`、`target_dir` 或状态目录写成绝对路径、盘符路径或包含 `..` 的路径
