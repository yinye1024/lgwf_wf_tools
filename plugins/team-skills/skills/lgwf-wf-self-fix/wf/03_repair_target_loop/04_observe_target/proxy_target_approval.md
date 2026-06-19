# 目标 Workflow 人工确认代理

workflow A 当前进入了自己的 `APPROVAL` 节点。请在当前对话中确认 approve 或 reject。

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

默认情况下，approve 的 `value` 应使用请求中的 `context`。如果你需要修改字段，请在 `value` 中给出完整 JSON object。
