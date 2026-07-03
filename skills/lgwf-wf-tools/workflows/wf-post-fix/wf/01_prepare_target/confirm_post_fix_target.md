# 确认 post-fix 目标

请确认要执行综合后处理的目标 workflow。提交 JSON：

```json
{
  "target_workflow_lgwf": "D:/example/workflow.lgwf",
  "target_package_root": "D:/example",
  "target_dirs": ["D:/example"],
  "mode": "manual"
}
```

- `target_workflow_lgwf` 必填。
- `target_package_root` 可省略，默认使用 `target_workflow_lgwf` 所在目录。
- `target_dirs` 可省略，默认使用 `target_package_root`。
- `mode` 可选 `manual` 或 `auto`，默认 `manual`。
