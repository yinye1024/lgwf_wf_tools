# Approval 规则

`waiting_human` 不是完成状态。

- 如果是 `flow.human_approval`，按 vendor main-agent ask flow 在当前对话确认并提交。
- 如果是 `AGENT_LOOP` 控制状态但没有 human request，汇报 loop reason、evidence 和 artifact 路径，等待用户决定。
- 只提交用户明确确认的 approval value。
- 提交包含中文或复杂嵌套的 approval/review value 时，优先使用 `scripts/safe_approval_submit.py`，通过 `--value-file` 或 `--value-json-base64` 传入 UTF-8 JSON；脚本会转换成 ASCII-only `--value-json` argv 后调用 facade，避免 PowerShell 参数层把中文写成 `????`。
- 只有确认 payload 是纯 ASCII 且结构简单时，才可直接调用 `approval submit --value-json` 或 `review submit --value-json`。
