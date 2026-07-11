# Workflow 输入

本文件说明 facade 如何准备内部 workflow 输入。

## 通用规则

- 先读取目标 workflow 的 `entry_contract.json`。
- `input_mode=input_json_required` 必须提供输入 JSON。
- `input_mode=tool_args` 由目标 tool workflow 自行解释参数。
- 包含中文、引号、换行或嵌套结构时，优先写入 UTF-8 no BOM 文件，再用 `--input-json-file`。

## 示例 LGWF 输入

```json
{
  "request": {
    "message": "hello"
  }
}
```

启动：

```powershell
$inputPath = "D:/tmp/facade-template-input.json"
$inputJson = @'
{
  "request": {
    "message": "hello"
  }
}
'@
[System.IO.File]::WriteAllText($inputPath, $inputJson, [System.Text.UTF8Encoding]::new($false))
python scripts\run_skill_workflow.py --workflow-id example-workflow --input-json-file $inputPath --lgwf-py <path-to-lgwf.py>
```

## 示例 tool workflow 输入

```powershell
python workflows\example-tool-workflow\scripts\example_tool.py --message "hello" --output .local\example-tool\result.json
```
