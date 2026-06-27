# Approval Worker Deprecated

本文只保留为历史说明。LGWF 不再支持或推荐独立 Codex approval window / approval worker 作为 human approval 交互路径。

当前统一协议是 main-agent ask flow：

- 启动 workflow 的主 agent 持续轮询同一个 `pid` / `work_dir`。
- 发现 `flow.human_approval` 等待时，主 agent 在当前对话读取 request 并询问用户 `approve` 或 `reject`。
- 主 agent 只写入 `created_by="main_agent_ask"` 的 controller payload。
- 主 agent 立即调用 `submit-human-controller-payload --final-user-confirmed true`，然后继续轮询原 workflow。

禁止事项：

- 不要启动新的交互窗口。
- 不要启动 approval worker。
- 不要使用 `approval_subagent` 或 `approval_codex_window` 作为 `created_by`。
- 不要调用 `respond-human-request` 作为普通 agent 路径。
- 不要直接写 `.response.json`。
