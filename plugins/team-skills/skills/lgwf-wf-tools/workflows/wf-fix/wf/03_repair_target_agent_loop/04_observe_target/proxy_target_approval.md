# 目标 Workflow 人工确认代理

workflow A 当前进入了自己的 `APPROVAL` 节点。请在当前对话中确认 approve 或 reject。

请先阅读请求中的目标 approval `prompt` 和 `context`。`value` 必须符合目标 approval 自己要求的输出格式，不要默认把整个 `context` 原样作为 `value`。

请返回以下 JSON object 之一：

```json
{
  "decision": "approve",
  "value": {}
}
```

```json
{
  "decision": "reject",
  "comment": "拒绝原因"
}
```

如果目标 prompt 要求类似 `{"approval":"approve","comment":""}` 的格式，则上面的 `value` 必须正是该 object。只有目标 prompt 明确要求返回完整 context 时，才把 context 作为 `value`。

提交该确认时，主 agent 不要把包含中文或其他非 ASCII 字符的 JSON 直接拼进 PowerShell/cmd 命令文本。必须使用 `scripts/safe_approval_submit.py`，并通过 UTF-8 `--value-file`、ASCII-only `--value-json-ascii` 或 UTF-8 base64 传递 payload。提交后读回 `.lgwf/human/*.response.json`，确认文本没有变成 `?` / `????`。
