---
name: lgwf-wf-tools
description: 当用户调用 /lgwf-wf-tools，或需要 LGWF 工作流入口路由请求、监控执行、处理工作流审批、运行入口初始化、诊断、列表命令，或基于执行证据改进路由和监控行为时使用。
---

# LGWF 工作流工具

本 skill 是 LGWF 工作流工具集合的统一入口。它对外只暴露一个入口，内部工作流统一放在 `workflows/*`，由根目录 `registry.json` 管理。

## 入口职责

- 根据用户目标路由到合适的内部工作流。
- 当用户明确使用 `run <path>`、`target-run <path>` 或 `--target-workflow <path>` 时，先按目标路径直启 LGWF workflow；不匹配时再进入内部工作流路由。
- 为外部 skill 提供脚本级代理入口 `scripts/run_skill_workflow.py`，把参数原样透传给本 skill 内置的 `vendor/lgwf-client-assist/scripts/lgwf.py run`。
- 围绕同一个 LGWF run handle 监控工作流执行、处理审批、解释状态和收尾。
- 根据真实执行中的路由、监控、审批、输入契约、报告、发布或文档问题进入自我优化。

## 强制第一跳

除 `/lgwf-wf-tools help`、`/lgwf-wf-tools 帮助` 或纯帮助请求外，处理任何工作流相关请求前必须先读取同目录 [AGENTS.md](AGENTS.md)。

读取 `AGENTS.md` 后再按它的规则执行：

- 如果请求显式匹配 `run <path>`、`target-run <path>` 或 `--target-workflow <path>`，必须先按 `AGENTS.md` 的目标 workflow 直启规则解析路径；解析失败时报告原因，不回退到内部工作流路由。
- 如果请求不匹配上述显式直启形式，路由前必须先列出 `registry.json` 中可用工作流。
- 必须说明为什么选择目标工作流。
- 必须读取目标工作流的 `AGENTS.md`。
- 必须遵守提案门禁、审批边界、监控循环和自我优化规则。

`/lgwf-wf-tools self-improve` 或 `/lgwf-wf-tools 自我优化` 必须进入自我优化路由，具体执行边界见 `AGENTS.md` 和 [docs/self-improve.md](docs/self-improve.md)。

内部工作流不是 Codex skill，不得单独暴露；它们的规则统一写在各自目录的 `AGENTS.md`。

## 帮助请求

`/lgwf-wf-tools help`、`/lgwf-wf-tools 帮助` 或纯帮助请求只展示帮助：

- 不修改文件。
- 不派发内部工作流。
- 不启动 LGWF run。
- 不运行会写 `.local/` 的自我优化命令。

帮助内容必须包含“可用指令”，并列出每个指令的简短用途和需要用户确认的操作。具体命令维护规则见 [docs/maintenance.md](docs/maintenance.md)。
