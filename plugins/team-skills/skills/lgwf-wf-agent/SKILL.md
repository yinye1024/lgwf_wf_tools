---
name: lgwf-wf-agent
description: Use when users invoke /lgwf-wf-agent or need LGWF workflow facade 初始化、doctor 检查、bundled client 同步、workflow 规划、修复、prompt 验收、prompt 升级、端到端测试生成、组合执行、运行监控或工作流问题沟通。
---

# LGWF Workflow Agent

本 skill 是 LGWF workflow 相关任务的对外唯一 agent 入口。它不是只转发单个 workflow 的薄 facade；它需要主动理解用户目标、澄清 workflow 相关问题、规划执行顺序，并按需要组合多个内部 workflow 完成任务。

处理 LGWF workflow 相关任务时，先读取同目录 `AGENTS.md`，再按 `registry.json` 选择或组合 `workflows/*` 下的内部 workflow。

内部 workflow 不是 Codex skill，不得作为独立 skill 暴露；它们的规则统一写在各自目录的 `AGENTS.md`。

## 显式命令

- `/lgwf-wf-agent`：先按 `AGENTS.md` 执行 doctor；如果未初始化但存在临时 zip，则自动 init；通过后再根据用户后续目标路由。
- `/lgwf-wf-agent init`：运行 `python scripts/init_lgwf_wf_agent.py`，同步临时 zip 到 vendor 并输出初始化报告。
- `/lgwf-wf-agent doctor`：运行 `python scripts/doctor_lgwf_wf_agent.py`，只读检查 facade 是否自包含；需要完整审计时使用 `python scripts/doctor_lgwf_wf_agent.py --deep`。
- `/lgwf-wf-agent list`：运行 `python scripts/list_workflows.py`，只读列出 `registry.json` 中可派发的内部 workflow。

## Agent 职责

- 主动和用户确认目标 workflow、期望结果、可接受的修改范围、是否需要人工确认、是否需要真实运行或只做审查。
- 当任务跨越多个阶段时，规划并串联内部 workflow，例如先 prompt 验收，再 prompt 升级，最后生成 E2E 测试。
- 在运行期间持续监控同一个 LGWF run handle，处理 approval、阻塞、失败诊断和后续分支选择。
- 结束时汇总已完成工作、关键产物、变更文件、剩余风险和下一步建议。
