# LGWF 启动规则

LGWF runtime workflow 必须使用 registry 中的固定路径启动，不得让用户手动拼接内部路径。

```powershell
$lgwfPy = "vendor/lgwf-client-assist/scripts/lgwf.py"
$inputPath = "D:/tmp/lgwf-input.json"
$inputJson = @'
{
  "key": "value"
}
'@
[System.IO.File]::WriteAllText($inputPath, $inputJson, [System.Text.UTF8Encoding]::new($false))
python $lgwfPy run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json-file $inputPath --background
```

启动前读取目标 workflow 的 `AGENTS.md`，并按需读取 `docs/workflow-inputs.md` 准备输入 JSON。
PowerShell 启动时默认使用 UTF-8 no BOM input JSON 文件；不要把包含中文、引号、换行或嵌套结构的 JSON 直接传给 `--input-json`。
