# Approval 规则

`waiting_human` 不是完成状态。

- 如果是 `flow.human_approval`，按 vendor main-agent ask flow 在当前对话确认并提交。
- 如果是 `AGENT_LOOP` 控制状态但没有 human request，汇报 loop reason、evidence 和 artifact 路径，等待用户决定。
- 只提交用户明确确认的 approval value。
- `approval submit --value-json` 不支持 file 参数；PowerShell 中用对象或 hashtable 生成 `ConvertTo-Json -Compress` 结果，先用 `ConvertFrom-Json` 校验，再把变量作为单个参数传给 `--value-json`。不要手写带反斜杠转义的 inline JSON。
