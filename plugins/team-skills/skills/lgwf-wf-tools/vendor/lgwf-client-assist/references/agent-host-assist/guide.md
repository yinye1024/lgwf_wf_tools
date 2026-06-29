# LGWF Agent Host 辅助

用于 Codex 主 agent 运行和跟踪 LGWF workflow。它接管会话层和用户交互层；workflow DSL 规则读取 `references/dsl-assist/guide.md`，prompt 规则读取 `references/prompt-assist/guide.md`，runtime/runner 调试读取 `references/runtime-assist/guide.md`。

## 使用入口

当任务涉及以下内容时，读取 `references/agent-host-assist/cli-agent-loop.md`：

- 后台启动 workflow 并持续轮询状态。
- 保存或恢复 `session_id`、`session_file`、`pid`、`work_dir`。
- 把 `status`、`log_tail`、`last_result`、`main_agent_status` 汇总成用户可读进展。
- 处理 `flow.human_approval` 的 main-agent ask 流程。
- 提交 `created_by="main_agent_ask"` 的 controller payload。
- workflow 完成后读取 run summary 和 changed files。

## 会话职责

- 启动 workflow 后保存返回的 `session_id` 和 `session_file`；兼容旧流程时保留 `pid` 和 `work_dir`。
- 每轮状态查询使用同一个 workflow handle。
- 等待下一轮状态时调用 `python <skill-dir>\scripts\lgwf.py wait`。

Agent 的全部运行、状态、审批和 run-record 操作统一通过 `scripts/lgwf.py`。
- 状态展示优先使用 `main_agent_status`；缺失时再从 `phase`、`current_node`、`current_capability`、`last_error` 和 pending human request 汇总。

## Human Approval

`flow.human_approval` 是当前 workflow loop 的等待状态。主 agent 在当前对话中读取 request、向用户询问 `approve` 或 `reject`，然后通过 controller payload 提交结果。

具体命令、payload 字段和状态机见 `references/agent-host-assist/cli-agent-loop.md`。
