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
- 用户要求给目标 workflow 生成自包含 self-improve 结构，或把 self-improve 通用模式安装到目标 workflow。
- 外部 skill 需要通过 `scripts/run_skill_workflow.py` 代理调用本 skill 内置 LGWF client。

## 第一跳

- 显式维护指令先按下表读取对应文档。
- 显式 workflow 意图、目标直启指令和其他 `/lgwf-wf-tools` 相关请求，读取同目录 [AGENTS.md](AGENTS.md)，由 workflow router 选择 `workflows/<id>`。

## 启动输入保护

- 通过 PowerShell 启动 `lgwf.py run` 或 `scripts/run_skill_workflow.py` 时，不要把 JSON 直接写进 `--input-json` 命令参数；即使是第一次启动，也优先创建 UTF-8 no BOM 临时 input JSON 文件，再使用 `--input-json-file <path>`。
- 只有确认 payload 是纯 ASCII 且非常简单时，才可临时使用 `--input-json "{}"`；包含中文、引号、换行或嵌套结构时必须使用文件方式，避免 PowerShell 转义导致参数损坏。
- 提交 `approval submit --value-json` 时 CLI 暂不支持 value file；在 PowerShell 中必须用对象或 hashtable 生成压缩 JSON，先用 `ConvertFrom-Json` 本地校验，再把变量作为单个 argv 参数传入，不要手写带转义引号的 JSON 字符串。
- 需要构造 workflow 输入时先读 [docs/workflow-inputs.md](docs/workflow-inputs.md)，再按目标 workflow `AGENTS.md` 的输入契约生成 JSON 文件。

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
| `/lgwf-wf-tools seed-self-improve <path>` | 读取 [AGENTS.md](AGENTS.md)，路由到 `self-improve-seed`。 |
| `/lgwf-wf-tools self-improve` | 读取 [AGENTS.md](AGENTS.md)，路由到 `self-improve`。 |
| `/lgwf-wf-tools 自我优化` | 读取 [AGENTS.md](AGENTS.md)，路由到 `self-improve`。 |
| `/lgwf-wf-tools 优化方案` | 读取 [AGENTS.md](AGENTS.md)，路由到 `self-improve`。 |

## 暴露边界

- 只暴露根目录 `SKILL.md` 作为 Codex skill。
- `workflows/*` 是内部 workflow package 或 tool workflow，不作为独立 Codex skill。
- `workflows/01-share/` 是共用规则目录，不注册为 workflow。
- `vendor/lgwf-client-assist/` 是内置运行客户端，不作为独立 Codex skill。
