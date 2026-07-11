# Facade Template 工作流路由表

## 模块类型

- `codex_skill`
- facade skill，内部 workflow 由 `registry.json` 管理。

## 模块定位

本文件负责把用户意图路由到 `registry.json` 中的 workflow。根 `SKILL.md` 只做第一跳；目标 workflow 的业务纪律由各自 `AGENTS.md` 承载。

创建、转换、修复或优化任何 skill/workflow 模块时，必须先读取 `workflows/01-share/module-contract.md`，确认模块类型、入口、依赖、状态边界、产物、验证和禁止事项。

## 入口

- Codex 入口：`SKILL.md`。
- 路由入口：本文件、`registry.json` 和每个 workflow 的 `entry_contract.json`。
- 维护入口：`docs/maintenance.md`。
- 内部 LGWF workflow 启动入口：`scripts/run_skill_workflow.py --workflow-id <id>`。

## 状态边界

- facade 本地状态写入 `.local/`。
- `kind=lgwf` 的 workflow 状态写入 registry 声明的 `work_dir/.lgwf/`。
- `kind=tool-workflow` 按自身 `AGENTS.md` 声明写入 `.local/`、目标目录或约定输出目录。

## Workflow 路由表

| 用户场景 | 选择 workflow |
| --- | --- |
| 需要演示一个 LGWF runtime workflow 的 registry 派发 | `example-workflow` |
| 需要演示一个脚本型内部 workflow | `example-tool-workflow` |

## 通用路由顺序

1. 判断请求是否是 `SKILL.md` 已处理的维护命令。
2. 从 Workflow 路由表选择一个 workflow id。
3. 读取 `registry.json`，确认目标 workflow 的 `kind`、路径、`entry_contract` 和 `agents_md`。
4. 读取目标 `entry_contract.json`，确认输入模式、required fields、状态边界和 `auto_human_policy`。
5. 读取目标 `AGENTS.md`。
6. 对 `kind=lgwf` 的内部 workflow，通过 `scripts/run_skill_workflow.py --workflow-id <id>` 启动。
7. 对 `kind=tool-workflow` 的内部 workflow，按目标 `AGENTS.md` 的入口执行。

## 输出要求

- 说明命中的用户场景。
- 说明选择的 workflow id 和 `kind`。
- 说明读取了 `registry.json`、哪个 `entry_contract.json` 和哪个目标 `AGENTS.md`。
- 如果没有选择 workflow，说明读取了哪份 facade 文档。

## 禁止事项

- 不要把内部 workflow 注册为独立 Codex skill。
- 不要绕过 `workflows/01-share/approval.md` 的人工确认展示模板。
- 不要在 registry 中保留不存在的 workflow entry。
- 不要让运行状态写入 workflow 源码目录。
