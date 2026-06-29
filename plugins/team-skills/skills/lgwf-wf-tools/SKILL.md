---
name: lgwf-wf-tools
description: Use when users invoke /lgwf-wf-tools or need the LGWF workflow facade to route a request to the right workflow, monitor execution, handle workflow approvals, run facade init/doctor/list, or improve routing/monitoring behavior from execution evidence.
---

# LGWF Workflow Tools

本 skill 是 LGWF workflow 工具集合的 facade 入口。它对外只暴露一个入口，内部 workflow 统一放在 `workflows/*`，由根目录 `registry.json` 管理。

核心职责只有三类：

1. 根据用户需求路由到合适的内部 workflow。
2. 围绕同一个 LGWF run handle 监控 workflow 执行、处理 approval、解释状态和收尾。
3. 根据真实执行中的路由、监控、approval 或报告问题，进入 self-improve 流程沉淀证据并生成可审查改进。

除 `help` 这类纯帮助请求外，处理 workflow 相关请求前先读取同目录 `AGENTS.md`，再按 `registry.json` 路由前必须先列出可用 workflow，并说明为什么选择目标 workflow。内部 workflow 不是 Codex skill，不得单独暴露；它们的规则统一写在各自目录的 `AGENTS.md`。

## 显式命令

- `/lgwf-wf-tools`：执行 doctor；如果未初始化但存在临时 zip，则自动 init 后再次 doctor；通过后再理解用户目标并路由。
- `/lgwf-wf-tools help` 或 `/lgwf-wf-tools 帮助`：只展示帮助，不修改文件，不派发内部 workflow，不启动 LGWF run。帮助内容必须包含“可用指令”，并列出每个指令的简短用途和需要用户确认的操作。
- `/lgwf-wf-tools init`：运行 `python scripts/init_lgwf_wf_tools.py`，同步临时 zip 到 vendor 并输出初始化报告。
- `/lgwf-wf-tools doctor`：运行 `python scripts/doctor_lgwf_wf_tools.py`，只读检查 facade 是否自包含；完整审计使用 `python scripts/doctor_lgwf_wf_tools.py --deep`。
- `/lgwf-wf-tools list`：运行 `python scripts/list_workflows.py`，只读列出 `registry.json` 中可派发的内部 workflow。
- `/lgwf-wf-tools self-improve` 或 `/lgwf-wf-tools 自我优化`：根据执行证据进入自我提升入口；只读检查可直接运行，记录 incident、生成 proposal 或提升 eval baseline 前必须说明证据、影响和确认边界。

`help` 至少列出：`/lgwf-wf-tools help`、`/lgwf-wf-tools init`、`/lgwf-wf-tools doctor`、`/lgwf-wf-tools list`、`/lgwf-wf-tools self-improve`、`/lgwf-wf-tools 优化方案`。

机器可读指令清单维护在 `commands.json`。需要做脚本级补齐时运行 `python scripts/complete_commands.py "<prefix>"`，例如 `python scripts/complete_commands.py "/lgwf-wf-tools d"`。

## Facade 职责

- 路由：先列出可用 workflow，再根据用户目标、目标目录、运行证据和 `registry.json` 选择一个最合适的 workflow，并说明选择理由。
- 监控：workflow 启动后保存同一个 `session_id` / `pid` / `work_dir`，后续 `status`、`wait`、`approval` 和 run artifact 查询都围绕同一个 handle 推进。
- 自我提升：当真实执行暴露 routing、monitoring、approval、input_contract、reporting、release 或 docs 问题时，先归类问题，再使用 `self-improve/scripts/self_improve.py` 生成报告、incident、proposal 或 eval 草稿。
- proposal 提醒：self-improve 收尾时，如果本次生成了 proposal 或发现已有待处理 proposal，必须提醒用户是否查看或执行 proposal；不直接执行 proposal，执行前必须先展示 review 计划并等待用户确认。
- 收尾：结束时汇总最终状态、关键产物、变更文件、阻塞项、剩余风险和建议下一步。

本 facade 不把“组合多个 workflow”作为默认职责。需要后续 workflow 时，应在当前 workflow 阶段完成后，基于结果证据重新路由并再次说明理由。
