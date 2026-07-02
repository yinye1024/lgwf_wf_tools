---
name: lgwf-wf-tools
description: 当用户调用 /lgwf-wf-tools，或需要 LGWF 工作流入口路由、运行监控、审批处理、初始化、诊断、列表或自我优化时使用。
---

# LGWF 工作流工具

本 skill 是 `lgwf-wf-tools` 的 bootstrap 指令分发器。它只做最小入口判断：显式维护命令路由到对应 facade 文档；其他 workflow 意图交给同目录 `AGENTS.md`。

## 使用场景

- 用户调用 `/lgwf-wf-tools`、`/lgwf-wf-tools help` 或 `/lgwf-wf-tools 帮助`。
- 用户要求初始化、诊断、列出、运行或继续 LGWF workflow。
- 用户要求修复、创建、优化、测试或规划 LGWF workflow package。
- 用户要求 self-improve、自我优化、复盘、沉淀 case 或生成 proposal。
- 外部 skill 需要通过 `scripts/run_skill_workflow.py` 代理调用本 skill 内置 LGWF client。

## 第一跳

- 显式维护指令先按下表读取对应文档。
- 显式 workflow 意图、目标直启指令和其他 `/lgwf-wf-tools` 相关请求，读取同目录 [AGENTS.md](AGENTS.md)，由 workflow router 选择 `workflows/<id>`。

## 显式指令

| 指令 | 下一步 |
| --- | --- |
| `/lgwf-wf-tools` | 读取 [docs/maintenance.md](docs/maintenance.md)。 |
| `/lgwf-wf-tools help` | 读取 [docs/maintenance.md](docs/maintenance.md)。 |
| `/lgwf-wf-tools 帮助` | 读取 [docs/maintenance.md](docs/maintenance.md)。 |
| `/lgwf-wf-tools init` | 读取 [docs/maintenance.md](docs/maintenance.md)。 |
| `/lgwf-wf-tools doctor` | 读取 [docs/maintenance.md](docs/maintenance.md)。 |
| `/lgwf-wf-tools list` | 读取 [docs/maintenance.md](docs/maintenance.md)。 |
| `/lgwf-wf-tools run <path>` | 读取 [AGENTS.md](AGENTS.md)，路由到 `target-run`。 |
| `/lgwf-wf-tools target-run <path>` | 读取 [AGENTS.md](AGENTS.md)，路由到 `target-run`。 |
| `/lgwf-wf-tools --target-workflow <path>` | 读取 [AGENTS.md](AGENTS.md)，路由到 `target-run`。 |
| `/lgwf-wf-tools self-improve` | 读取 [AGENTS.md](AGENTS.md)，路由到 `self-improve`。 |
| `/lgwf-wf-tools 自我优化` | 读取 [AGENTS.md](AGENTS.md)，路由到 `self-improve`。 |
| `/lgwf-wf-tools 优化方案` | 读取 [AGENTS.md](AGENTS.md)，路由到 `self-improve`。 |

## 暴露边界

- 只暴露根目录 `SKILL.md` 作为 Codex skill。
- `workflows/*` 是内部 workflow package 或 tool workflow，不作为独立 Codex skill。
- `workflows/01-share/` 是共用规则目录，不注册为 workflow。
- `vendor/lgwf-client-assist/` 是内置运行客户端，不作为独立 Codex skill。
