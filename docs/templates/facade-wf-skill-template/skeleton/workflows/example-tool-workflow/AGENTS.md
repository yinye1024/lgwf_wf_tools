# example-tool-workflow 指引

本目录是 facade 内部的示例 `tool_workflow`，不是 LGWF runtime workflow，也不是独立 Codex skill。

## 模块契约

- 模块类型：`tool_workflow`。
- registry id：`example-tool-workflow`。
- 入口：`workflows/example-tool-workflow/scripts/example_tool.py`。
- 入口字段和输入示例以 `entry_contract.json` 为准。

## 状态边界

脚本输出由 `--output` 指定。默认建议写入 `.local/example-tool-workflow/`，不要写入源码目录。

## 执行

```powershell
python workflows\example-tool-workflow\scripts\example_tool.py --message "hello" --output .local\example-tool-workflow\result.json
```

## 验证

```powershell
python scripts\validate_registry.py
python workflows\example-tool-workflow\scripts\example_tool.py --message "hello" --output .local\example-tool-workflow\result.json
```

## 禁止事项

- 不要要求 LGWF runtime audit。
- 不要自动提交 approval。
- 不要把运行输出写入发布包基线。
