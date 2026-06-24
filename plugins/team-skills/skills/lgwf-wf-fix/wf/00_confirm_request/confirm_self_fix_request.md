# 确认 Fix 目标

请确认要修复的目标 workflow 和 fix 参数。

返回值必须是 JSON object，格式如下：

```json
{
  "target_workflow_lgwf": "D:/path/to/workflow.lgwf",
  "max_attempts": 5,
  "ask_main_agent_for_target_approvals": false
}
```

- `target_workflow_lgwf`: 必填，目标 `workflow.lgwf` 文件路径。
- `max_attempts`: 可选，最大修复尝试次数，默认 `5`。
- `ask_main_agent_for_target_approvals`: 可选，是否让 `lgwf-wf-fix` 把目标 workflow 的 `APPROVAL` 转发到当前主 agent 对话中确认，默认 `false`。

确认后，workflow 会读取目标目录，分析目标 workflow 的启动参数契约，然后单独收集目标 workflow 的 `--input-json`。

主 agent 提交该 JSON 时不要把包含中文或其他非 ASCII 字符的 payload 直接拼进 PowerShell/cmd 命令文本。必须使用 `scripts/safe_approval_submit.py`，通过 UTF-8 `--value-file`、ASCII-only `--value-json-ascii` 或 UTF-8 base64 传递，并在提交后读回 `.lgwf/human/*.response.json` 确认没有出现 `?` / `????` 编码损坏。
