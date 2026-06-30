# 目标 Workflow 人工确认代理

workflow A 当前进入了自己的 `APPROVAL` 节点。请在当前对话中确认 approve 或 reject。

请先阅读请求中的目标 approval `prompt` 和 `context`。`value` 必须符合目标 approval 自己要求的输出格式，不要默认把整个 `context` 原样作为 `value`。

请返回以下 JSON object 之一：

```json
{
  "decision": "approve",
  "value": {
    "decision": "approve",
    "comment": "确认说明",
    "tuning": {
      "workflow_sequence_changes": [],
      "extra_constraints": [],
      "acceptance_changes": []
    }
  }
}
```

```json
{
  "decision": "reject",
  "comment": "拒绝原因"
}
```

如果目标 prompt 要求类似 `{"approval":"approve","comment":""}` 的格式，则上面的 `value` 必须正是该 object。只有目标 prompt 明确要求返回完整 context 时，才把 context 作为 `value`。

注意这里有两层 approval：

- 外层是本代理节点的确认结果，必须是 `{"decision":"approve","value": <目标 approval 输出>}`。
- 内层是目标 workflow 自己的 approval 输出，必须严格按目标 prompt 的 `Output Format` 填入外层 `value`。

如果用户只回复 `approve` 且没有提供外层 `value`，代理只会提交空 object `{}` 作为目标 value；不会默认转发完整 `context`。当目标 prompt 要求结构化输出时，主 agent 必须把该结构化输出填入外层 `value`。只有目标 prompt 明确要求完整 `context` 时，才允许把完整 `context` 放进外层 `value`。

提交该确认时，主 agent 不要把包含中文或其他非 ASCII 字符的 JSON 直接拼进 PowerShell/cmd 命令文本。必须使用 `workflows/wf-fix/scripts/safe_approval_submit.py`（相对 `lgwf-wf-tools` skill 根目录），并通过 UTF-8 `--value-file`、ASCII-only `--value-json-ascii` 或 UTF-8 base64 传递 payload。提交后读回 `.lgwf/human/*.response.json`，确认文本没有变成 `?` / `????`。
