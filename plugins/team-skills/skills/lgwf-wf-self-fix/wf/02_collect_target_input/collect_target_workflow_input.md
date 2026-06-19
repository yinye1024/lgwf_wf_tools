# 目标 Workflow 启动参数确认

请根据 `.lgwf/target_input_contract.json` 中的字段说明，提供 workflow A 的启动参数 JSON object。

返回值必须是 JSON object。该对象会保存为 `.lgwf/target_workflow_input.json`，后续每一轮运行 workflow A 都会原样作为 `--input-json` 传入，不会再次询问。

示例：

```json
{
  "example_field": "example value"
}
```

如果需要调整字段，请直接返回最终 JSON object。
