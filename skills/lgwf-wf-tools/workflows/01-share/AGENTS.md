# Workflow 共用规则

本目录保存 `lgwf-wf-tools` 内部 workflow 共享的执行规则。具体 workflow 的 `AGENTS.md` 必须先声明需要读取哪些共用文档，再补充自己的输入、输出和确认边界。

## 引用方式

- LGWF runtime workflow 通常读取 `module-contract.md`、`registry-contract.md`、`lgwf-dispatch.md`、`lgwf-monitor.md`、`approval.md` 和 `artifacts.md`。
- 非 LGWF 的 `tool-workflow` 通常读取 `module-contract.md`、`registry-contract.md`、`tool-workflow.md` 和 `artifacts.md`。
- 创建、转换、修复或优化 skill/workflow 模块时，必须先读取 facade 根目录 `docs/LGWF_WF_MODULAR_DEVELOPMENT.md`，再读取 `module-contract.md`，先确认目录边界、子 workflow/复杂 step 拆分方式、模块类型和自包含契约。
- 如果目标 workflow 的 `AGENTS.md` 与共用规则冲突，必须说明冲突原因，并优先遵循目标 workflow 的显式规则；但目标规则不得降低 `approval.md` 中的人工确认展示模板要求。

## 共享边界

- `workflows/01-share/` 不注册到 `registry.json`，不作为可派发 workflow。
- 本目录不得包含 `SKILL.md`。
- 本目录只放通用规则，不放具体 workflow 的业务逻辑。
