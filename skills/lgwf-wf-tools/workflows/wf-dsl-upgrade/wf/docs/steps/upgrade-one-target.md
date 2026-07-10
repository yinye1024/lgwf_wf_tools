# upgrade_one_target 步骤说明

## 目标

对 `FOREACH` 当前 item 指向的单个 `.lgwf` 文件执行 audit、必要修复、复检和结果固化。

## 输入

- `state.wf_dsl_upgrade.current_target`
- `state.wf_dsl_upgrade.current_index`

## 输出

- `state.wf_dsl_upgrade.current_result`
- `ws/.lgwf/current_target_context.json`
- `ws/.lgwf/current_target_audit.json`

## 执行规则

- `prepare_repair_context` 校验当前目标是否仍在授权边界内，并输出 `TARGET_FILES`。
- `audit_current_target` 先运行真实 authoring audit。
- `mode=dry_run` 或 audit 已通过时直接 finalize。
- `mode=apply` 且 audit 未通过时进入 `REACT repair_target MAX 3`。
- Codex 只能通过 `TARGET_FILES state.wf_dsl_upgrade.target_files` 修改当前 `.lgwf` 文件。
- `DECIDE PY` 负责复跑 audit，并写入 `next=continue` 或 `next=exit`。

## 验证

```powershell
$lgwfRepo = "<lgwf-repo>"
$env:PYTHONPATH = "$lgwfRepo\src"
& "$lgwfRepo\.venv\Scripts\python.exe" -m lgwf_dsl.cli audit skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\wf\03_upgrade_one_target\workflow.lgwf
```
