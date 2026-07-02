# LGWF 启动规则

LGWF runtime workflow 必须使用 registry 中的固定路径启动，不得让用户手动拼接内部路径。

```powershell
$lgwfPy = "vendor/lgwf-client-assist/scripts/lgwf.py"
python $lgwfPy run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json <json> --background
```

启动前读取目标 workflow 的 `AGENTS.md`，并按需读取 `docs/workflow-inputs.md` 准备输入 JSON。
