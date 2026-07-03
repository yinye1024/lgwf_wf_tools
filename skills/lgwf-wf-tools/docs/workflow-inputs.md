# 各 Workflow 输入摘要

本文只保存 facade 准备 `--input-json` 时的常用摘要。最终以对应 workflow `AGENTS.md` 的输入契约为准。

## PowerShell 输入建议

在 PowerShell 中不要把 JSON 直接塞进 `--input-json`，否则双引号容易被 shell 处理掉，中文和换行也可能在命令参数层损坏。第一次启动也默认先把 JSON 写入 UTF-8 no BOM 文件，再使用 `--input-json-file`：

```powershell
$inputPath = "D:/tmp/lgwf-input.json"
$inputJson = @'
{
  "raw_intent": "要创建的新 LGWF workflow 原始意图"
}
'@
[System.IO.File]::WriteAllText($inputPath, $inputJson, [System.Text.UTF8Encoding]::new($false))

python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py run --workflow-lgwf <workflow.lgwf> --work-dir <ws> --input-json-file $inputPath --background
```

也可以使用 `--input-json @D:/tmp/lgwf-input.json`。新脚本仍兼容原有 `--input-json '{"key":"value"}'`，但不建议在 PowerShell 中使用；只有纯 ASCII 的空对象 `--input-json "{}"` 可作为临时 smoke 用法。

## wf-fix

`wf-fix` 启动时使用空 JSON object：

```json
{}
```

它会在第一个 approval 中询问 `target_workflow_lgwf`、`max_attempts` 和 `ask_main_agent_for_target_approvals`，随后再收集目标 workflow 自己的业务输入。

## wf-prompt-fix

推荐输入：

```json
{
  "prompt_fix_target": {
    "target_workflow_lgwf": "D:/example/workflow.lgwf",
    "target_package_root": "D:/example",
    "target_dirs": ["D:/example"]
  }
}
```

## wf-prompt-upgrade

推荐输入：

```json
{
  "prompt_upgrade_target": {
    "target_workflow_lgwf": "D:/example/workflow.lgwf",
    "target_package_root": "D:/example",
    "target_dirs": ["D:/example"]
  }
}
```

## wf-create

推荐输入：

```json
{
  "raw_intent": "要创建的新 LGWF workflow 原始意图"
}
```

## wf-convert

推荐输入：

```json
{
  "prompt_convert_target": {
    "target_dir": "D:/example/prompt-workflow",
    "entry_files": ["README.md"],
    "target_workflow_name": "example-workflow",
    "target_package_root": "skills/example-workflow"
  }
}
```

## e2e-test-generator

`e2e-test-generator` 会通过入口 approval 收集目标信息，目标 JSON 形态为：

```json
{
  "workflow_lgwf": "D:/example/workflow.lgwf",
  "workflow_root": "D:/example",
  "test_output_dir": "tests",
  "test_name_prefix": "example_workflow"
}
```

## plan

推荐输入：

```json
{
  "react_task_request": {
    "objective": "要完成的复杂任务目标",
    "target_type": "modify_artifact",
    "analysis_target_files": ["D:/example/path/to/file.md"],
    "constraints": ["先生成计划和验收契约，用户确认后再修改目标文件"]
  }
}
```
