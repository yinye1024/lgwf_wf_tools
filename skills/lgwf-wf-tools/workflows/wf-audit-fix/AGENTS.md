# wf-audit-fix 工作流指引

本目录是 `lgwf-wf-tools` facade 通过 `registry.json` 派发的内部 `lgwf_workflow_package`。它负责对已授权的 LGWF workflow 执行 audit 静态修复：收集授权目标、确认目标范围、通过 `FOREACH` 逐个运行真实 authoring audit、必要时由 Codex 做最小修复、复检并汇总结果。

## 模块定位

- 模块类型：`lgwf_workflow_package`。
- registry id：`wf-audit-fix`。
- 不是独立 Codex skill，不得单独注册。
- 只处理 manifest 授权范围内的 `.lgwf` 文件，不运行业务 workflow。
- 根 workflow 使用 `FOREACH upgrade_each` 调度 `03_upgrade_one_target`；不要退回 Python 批处理循环。

## 入口

- workflow root：`wf/`
- workflow 入口：`wf/workflow.lgwf`
- work dir：`ws/`
- 机器入口契约：`entry_contract.json`
- 入口 JSON 顶层字段为 `audit_fix_target`；其中 `target_paths` 和 `allowed_dirs` 必填，`mode` 默认按脚本归一化为 `dry_run`，`scope_mode` 默认 `explicit`。
- facade 启动命令示例：

```powershell
$lgwfPy = "skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy run --workflow-lgwf skills\lgwf-wf-tools\workflows\wf-audit-fix\wf\workflow.lgwf --work-dir skills\lgwf-wf-tools\workflows\wf-audit-fix\ws --input-json-file D:\tmp\wf-audit-fix-input.json --background
```

## 依赖

- 依赖 LGWF runtime 支持 authoring `FOREACH` / runtime `subgraph.foreach`。
- 依赖 `skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py` 执行真实 audit；若 bundled vendor 尚未刷新到支持 `FOREACH` 的 wheel，则源码 audit 可临时使用已更新的 LGWF 主仓库 runtime，正式运行前必须刷新 vendor。
- 依赖 `workflows/01-share/module-contract.md` 的模块契约，以及 `workflows/01-share/` 下的 dispatch、monitor、approval 和 artifacts 共享规则。
- 依赖 `wf/shared/scripts/dsl_upgrade_common.py` 提供 package 级 UTF-8 JSON、路径校验、hash、audit 调用和诊断键归一化。
- `03_upgrade_one_target` 由 `RUN_WORKFLOW` 作为子包快照执行，阶段脚本必须使用本地 `scripts/dsl_upgrade_common.py`，不得运行时回查父级 `wf/shared`。

## 状态边界

- 运行状态只允许写入 `ws/.lgwf/` 和 `ws/reports/`。
- workflow 源码树只保存 `wf/`、`tests/`、`scripts/`、入口文档和静态资源，不保存运行态 `.lgwf/`、`__pycache__/` 或临时输出。
- 目标文件写入只允许发生在 `mode=apply` 且 `state.wf_audit_fix.confirm_scope_result.decision=approve` 时；`.lgwf/scope_approval.json` 保存已批准的业务范围 context，不作为控制分支的 decision 来源。当前 `FOREACH` item 必须同时位于 `target_manifest.json` 与 `allowed_dirs` 内；`scope_mode=explicit` 的 `target_paths` 可传 `.lgwf` 文件或目录，目录会递归展开为 `.lgwf` 文件列表。
- Codex 修复节点只能通过 `TARGET_FILES state.wf_audit_fix.target_files` 访问当前 `.lgwf` 文件。
- `dry_run` 不进入写入式修复，只记录 audit 结果并汇总。
- package 内资源路径、`workflow.lgwf` 引用路径和文档示例路径必须使用包内相对路径，禁止绝对路径、盘符路径和 `..`。

## 产物

- `.lgwf/target_manifest.json`
- `.lgwf/target_scope_validation.json`
- `.lgwf/scope_confirmation_context.json`
- `.lgwf/scope_approval.json`
- `.lgwf/foreach/upgrade_each/items/{index}/.lgwf/current_target_context.json`
- `.lgwf/foreach/upgrade_each/items/{index}/.lgwf/current_target_audit.json`
- `.lgwf/result_summary.json`
- `reports/wf-audit-fix/report.md`

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-audit-fix\tests
$lgwfRepo = "<lgwf-repo>"
$env:PYTHONPATH = "$lgwfRepo\src"
& "$lgwfRepo\.venv\Scripts\python.exe" -m lgwf_dsl.cli audit skills\lgwf-wf-tools\workflows\wf-audit-fix\wf\workflow.lgwf
```

## 禁止事项

- 不得把本 workflow 注册为独立 Codex skill。
- 不得读取或修改未进入 manifest 的文件。
- 不得在 `dry_run` 下写入目标文件。
- 不得绕过 `02_confirm_scope` 的人工确认直接进入 `FOREACH`。
- 不得把 `reject` 路由成 `FAIL_ALL`，必须允许进入总结阶段。
- 不得把阶段私有逻辑塞进根 `wf/workflow.lgwf`。
- 不得在子 workflow 目录下继续创建孙级 `workflow.lgwf`。
- 不得写入源码树 `.lgwf/`、`__pycache__/` 或占位运行产物。
