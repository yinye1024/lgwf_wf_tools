# 确认 Self-Fix 目标

请确认要修复的目标 workflow 和 self-fix 参数。

返回值必须是 JSON object，格式如下：

```json
{
  "target_workflow_lgwf": "D:/path/to/workflow.lgwf",
  "max_attempts": 5
}
```

- `target_workflow_lgwf`：必填，目标 `workflow.lgwf` 文件路径。
- `max_attempts`：可选，最大修复尝试次数，默认 `5`。

确认后，workflow 会读取目标目录，分析目标 workflow 的业务启动参数，并在下一步再次请求确认目标 workflow 的 `--input-json`。
