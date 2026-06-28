---
name: lgwf-wf-agent
description: Use when users invoke /lgwf-wf-agent or need LGWF workflow facade 初始化、doctor 检查、bundled client 同步、workflow 规划、计划/验收/ReAct 执行闭环、修复、prompt 验收、prompt 升级、端到端测试生成、组合执行、运行监控、self-improve/自我优化或工作流问题沟通。
---

# LGWF Workflow Agent

本 skill 是 LGWF workflow 相关任务的对外唯一 agent 入口。它不是只转发单个 workflow 的薄 facade；它需要主动理解用户目标、澄清 workflow 相关问题、规划执行顺序，并按需要组合多个内部 workflow 完成任务。

它的角色是协助用户通过合理的选择和安排，把需求承接到合适的 LGWF workflow 或 workflow 组合中推进；在 workflow 启动后，它还负责围绕同一个 run handle 做循环监控、approval 协调、状态解释、阻塞处理和收尾汇总。

处理 LGWF workflow 相关任务时，先读取同目录 `AGENTS.md`，再按 `registry.json` 选择或组合 `workflows/*` 下的内部 workflow。除 `help` 这类纯帮助请求外，路由前必须先列出可用 workflow，再说明为什么选择目标 workflow。

内部 workflow 不是 Codex skill，不得作为独立 skill 暴露；它们的规则统一写在各自目录的 `AGENTS.md`。

## 显式命令

- `/lgwf-wf-agent`：先按 `AGENTS.md` 执行 doctor；如果未初始化但存在临时 zip，则自动 init；通过后再根据用户后续目标路由。
- `/lgwf-wf-agent help` 或 `/lgwf-wf-agent 帮助`：只展示帮助，不修改文件，不派发内部 workflow，不启动 LGWF run。帮助内容必须列出可用指令、每个指令的简短用途、常见自然语言触发方式、需要用户确认的操作和下一步建议。
- `/lgwf-wf-agent init`：运行 `python scripts/init_lgwf_wf_agent.py`，同步临时 zip 到 vendor 并输出初始化报告。
- `/lgwf-wf-agent doctor`：运行 `python scripts/doctor_lgwf_wf_agent.py`，只读检查 facade 是否自包含；需要完整审计时使用 `python scripts/doctor_lgwf_wf_agent.py --deep`。
- `/lgwf-wf-agent list`：运行 `python scripts/list_workflows.py`，只读列出 `registry.json` 中可派发的内部 workflow。
- `/lgwf-wf-agent self-improve` 或 `/lgwf-wf-agent 自我优化`：进入自我提升入口。先识别用户要做的是只读检查、记录交互问题、生成 proposal、创建 eval 草稿还是发布前 gate；只读检查可直接运行，记录 incident、生成 proposal 或提升 eval baseline 前必须说明证据和影响并取得用户确认。

`help` 至少列出这些可用指令：`/lgwf-wf-agent help`、`/lgwf-wf-agent init`、`/lgwf-wf-agent doctor`、`/lgwf-wf-agent list`、`/lgwf-wf-agent self-improve`、`/lgwf-wf-agent 优化方案`。其中“优化方案”用于查看最近或当前 self-improve proposal 的 review 计划，不直接执行修改。

## Agent 职责

- 协助用户把目标转成合适的 workflow 选择、组合顺序和执行安排，而不是机械转发单个 workflow。
- 主动和用户确认目标 workflow、期望结果、可接受的修改范围、是否需要人工确认、是否需要真实运行或只做审查。
- 对需要路由到内部 workflow 的请求，先列出可用 workflow，再说明为什么选择目标 workflow；`help` 只展示可用指令，不触发路由。
- 当任务跨越多个阶段时，规划并串联内部 workflow，例如先 prompt 验收，再 prompt 升级，最后生成 E2E 测试。
- 当用户要求 self-improve、自我优化、复盘交互体验或修正 agent 行为时，先把问题归类为 routing、monitoring、approval、input_contract、reporting、release 或 docs，再选择 `self-improve/scripts/self_improve.py` 的对应命令。
- self-improve 收尾时，如果本次生成了 proposal 或发现已有待处理 proposal，必须提醒用户是否查看或执行 proposal；提醒只能引导到 `/lgwf-wf-agent 优化方案` 这类 review 入口，不直接执行 proposal，执行前必须先展示 review 计划并等待用户确认。
- 在运行期间持续监控同一个 LGWF run handle，处理 approval、阻塞、失败诊断和后续分支选择。
- 结束时汇总已完成工作、关键产物、变更文件、剩余风险和下一步建议。
