---
name: lgwf-wf-tools
description: Use when users invoke /lgwf-wf-tools or need the LGWF workflow facade to route a request to the right workflow, monitor execution, handle workflow approvals, run facade init/doctor/list, or improve routing/monitoring behavior from execution evidence.
---

# LGWF Workflow Tools

本 skill 是 LGWF workflow 工具集合的 facade 入口。它对外只暴露一个入口，内部 workflow 统一放在 `workflows/*`，由根目录 `registry.json` 管理。

## 入口职责

- 根据用户目标路由到合适的内部 workflow。
- 围绕同一个 LGWF run handle 监控 workflow 执行、处理 approval、解释状态和收尾。
- 根据真实执行中的 routing、monitoring、approval、input_contract、reporting、release 或 docs 问题进入 self-improve。

## 强制第一跳

除 `/lgwf-wf-tools help`、`/lgwf-wf-tools 帮助` 或纯帮助请求外，处理任何 workflow 相关请求前必须先读取同目录 [AGENTS.md](AGENTS.md)。

读取 `AGENTS.md` 后再按它的规则执行：

- 路由前必须先列出 `registry.json` 中可用 workflow。
- 路由前必须先列出可用 workflow。
- 必须说明为什么选择目标 workflow。
- 必须读取目标 workflow 的 `AGENTS.md`。
- 必须遵守 proposal gate、approval 边界、监控循环和 self-improve 规则。

`/lgwf-wf-tools self-improve` 或 `/lgwf-wf-tools 自我优化` 必须进入 self-improve 路由，具体执行边界见 `AGENTS.md` 和 [docs/self-improve.md](docs/self-improve.md)。

内部 workflow 不是 Codex skill，不得单独暴露；它们的规则统一写在各自目录的 `AGENTS.md`。

## 帮助请求

`/lgwf-wf-tools help`、`/lgwf-wf-tools 帮助` 或纯帮助请求只展示帮助：

- 不修改文件。
- 不派发内部 workflow。
- 不启动 LGWF run。
- 不运行会写 `.local/` 的 self-improve 命令。

帮助内容必须包含“可用指令”，并列出每个指令的简短用途和需要用户确认的操作。具体命令维护规则见 [docs/maintenance.md](docs/maintenance.md)。
