# Registry 契约

`registry.json` 是 facade 的唯一 workflow 注册表。根 `AGENTS.md` 选择 workflow 后，必须读取 registry 条目和目标 `AGENTS.md`。

## 通用字段

- `id`：workflow 唯一标识。
- `kind`：执行类型，当前支持 `lgwf` 和 `tool-workflow`。
- `description`：面向人的中文说明。
- `agents_md`：目标 workflow 的引导文件，相对 facade 根目录。
- `entry_contract`：目标 workflow 的机器可读入口契约。

## `lgwf`

`kind: "lgwf"` 必须包含：

- `workflow_lgwf`：可运行的 `workflow.lgwf` 文件。
- `work_dir`：固定运行目录，不得等于 workflow 源码目录。
- `agents_md`：目标 workflow 的引导文件。
- `entry_contract`：目标 workflow 的入口契约。

## `tool-workflow`

`kind: "tool-workflow"` 必须包含：

- `entry`：主脚本或文档入口，相对 facade 根目录。
- `agents_md`：目标 workflow 的引导文件。
- `entry_contract`：目标 workflow 的入口契约。

`tool-workflow` 不要求 `workflow_lgwf` 或 `work_dir`，也不得走 LGWF runtime audit。
