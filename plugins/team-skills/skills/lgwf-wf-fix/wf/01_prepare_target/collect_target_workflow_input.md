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

主 agent 提交该 JSON 时不要把包含中文或其他非 ASCII 字符的 payload 直接拼进 PowerShell/cmd 命令文本。必须使用 `scripts/safe_approval_submit.py`，通过 UTF-8 `--value-file`、ASCII-only `--value-json-ascii` 或 UTF-8 base64 传递，并在提交后读回 `.lgwf/human/*.response.json` 确认没有出现 `?` / `????` 编码损坏。
