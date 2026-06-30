# 各 Workflow 输入摘要

本文只保存 facade 准备 `--input-json` 时的常用摘要。最终以对应 workflow `AGENTS.md` 的输入契约为准。

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
