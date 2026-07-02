# intake_request

读取审批请求，提取 requester、amount、risk_level、purpose，并检查字段是否完整。

输出 JSON：

```json
{
  "requester": "alice",
  "amount": 1200,
  "risk_level": "high",
  "purpose": "vendor payment",
  "missing_fields": []
}
```

