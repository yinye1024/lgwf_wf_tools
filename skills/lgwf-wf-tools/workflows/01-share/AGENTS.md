# Workflow 共用规则

本目录保存 `lgwf-wf-tools` 内部 workflow 共享的执行规则。具体 workflow 的 `AGENTS.md` 必须先声明需要读取哪些共用文档，再补充自己的输入、输出和确认边界。

## 引用方式

- LGWF runtime workflow 通常读取 `registry-contract.md`、`lgwf-dispatch.md`、`lgwf-monitor.md`、`approval.md` 和 `artifacts.md`。
- 非 LGWF 的 `tool-workflow` 通常读取 `registry-contract.md`、`tool-workflow.md` 和 `artifacts.md`。
- 如果目标 workflow 的 `AGENTS.md` 与共用规则冲突，必须说明冲突原因，并优先遵循目标 workflow 的显式规则。

## 共享边界

- `workflows/01-share/` 不注册到 `registry.json`，不作为可派发 workflow。
- 本目录不得包含 `SKILL.md`。
- 本目录只放通用规则，不放具体 workflow 的业务逻辑。
