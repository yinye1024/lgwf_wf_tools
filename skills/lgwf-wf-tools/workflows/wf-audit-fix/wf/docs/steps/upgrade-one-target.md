# upgrade_one_target 步骤说明

## 目标

对 `FOREACH` 当前 item 指向的单个 `.lgwf` 文件执行 audit、必要修复、复检和结果固化。

## 输入

- `state.wf_audit_fix.current_target`
- `state.wf_audit_fix.current_index`

## 输出

- `state.wf_audit_fix.current_result`
- `ws/.lgwf/current_target_context.json`
- `ws/.lgwf/current_target_audit.json`

## 执行规则

- `prepare_repair_context` 校验当前目标是否仍在授权边界内，并输出 `TARGET_FILES`。
- 阶段脚本使用 `03_upgrade_one_target/scripts/dsl_upgrade_common.py`，保持 `RUN_WORKFLOW` 子包快照自包含；不得依赖父级 `wf/shared/scripts` 才能导入。
- `audit_current_target` 先运行真实 authoring audit。
- `mode=dry_run` 或 audit 已通过时直接 finalize。
- `mode=apply` 且 audit 未通过时进入 `REACT repair_target MAX 3`。
- `REASON CODEX` 只读取第 0 次或上一轮 `OBSERVE PY` 写回的 audit check diagnostics，逐条生成修正方案，不修改文件。
- `ACT CODEX` 只执行 reason 的修正方案，只允许修改 `TARGET_FILES` 中的当前 `.lgwf` 文件。
- `OBSERVE PY` 运行 `scripts/observe_repair.py` 复跑 audit check，写入 `.lgwf/current_target_audit.json` 和 `.lgwf/repair_observation.json`。
- Codex 只能通过 `TARGET_FILES state.wf_audit_fix.target_files` 修改当前 `.lgwf` 文件。
- `DECIDE PY` 消费 `OBSERVE PY` 的结构化观察，并写入 `next=continue` 或 `next=exit`。

## 验证

```powershell
python -m unittest skills.lgwf-wf-tools.workflows.wf-audit-fix.tests.test_wf_script_flow_e2e.ScriptFlowE2ETest.test_per_target_scripts_import_from_standalone_child_package
$lgwfRepo = "<lgwf-repo>"
$env:PYTHONPATH = "$lgwfRepo\src"
& "$lgwfRepo\.venv\Scripts\python.exe" -m lgwf_dsl.cli audit skills\lgwf-wf-tools\workflows\wf-audit-fix\wf\03_upgrade_one_target\workflow.lgwf
```
