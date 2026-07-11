# wf-audit-fix

`wf-audit-fix` 是 `lgwf-wf-tools` facade 内部的 `lgwf_workflow_package`，用于在明确授权边界内对 LGWF `.lgwf` 文件执行 audit 静态修复。它先从显式文件或目录输入收集并冻结授权目标，再经人工确认后使用 `FOREACH` 逐个目标运行 audit 与 per-target repair loop，最后汇总每个目标的结果。

## 模块定位

- 模块类型：`lgwf_workflow_package`。
- registry id：`wf-audit-fix`。
- 这是 facade 派发的内部 workflow，不是独立 Codex skill，不得单独注册或绕过 facade 入口运行治理。
- 处理对象仅限 manifest 授权范围内的 `.lgwf` 文件；不运行业务 workflow，只做 DSL authoring audit、Codex 最小修复与复检。

## 入口

- workflow package root：`wf/`
- workflow 入口：`wf/workflow.lgwf`
- 固定 work dir：`ws/`
- 机器入口契约：`entry_contract.json`
- 人类入口文档：`README.md`、`AGENTS.md`
- facade 启动命令示例：

```powershell
$lgwfPy = "skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy run --workflow-lgwf skills\lgwf-wf-tools\workflows\wf-audit-fix\wf\workflow.lgwf --work-dir skills\lgwf-wf-tools\workflows\wf-audit-fix\ws --input-json-file D:\tmp\wf-audit-fix-input.json --background
```

- 入口 JSON 通过 `entry_contract.json` 约束，核心字段如下：

```json
{
  "audit_fix_target": {
    "target_paths": ["D:/example"],
    "mode": "dry_run",
    "allowed_dirs": ["D:/example"],
    "scope_mode": "explicit",
    "max_targets": 8
  }
}
```

- `scope_mode=explicit` 支持在 `target_paths` 中传入 `.lgwf` 文件或目录；目录会递归扫描所有 `.lgwf` 文件并写入 manifest，同时输出 `state.wf_audit_fix.targets` 供 `FOREACH` 消费。
- `allowed_dirs` 必填，用于在 `dry_run` 和 `apply` 下统一证明目标范围已授权；缺少可用授权目录时入口校验会失败。
- 第一版保留 `scope_mode=registry` 契约和显式 unsupported 行为，不会静默降级为 `explicit`。

## 依赖

- 依赖 `skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py` 执行真实 `audit`。
- 依赖 `workflows/01-share/` 的模块契约、dispatch、monitor、approval 和 artifacts 共享规则。
- 依赖 `wf/shared/scripts/dsl_upgrade_common.py` 统一处理 package 级 UTF-8 JSON、路径授权、hash、audit 调用和诊断键归一化。
- `03_upgrade_one_target` 作为 `RUN_WORKFLOW` 子包执行时使用阶段内 `scripts/dsl_upgrade_common.py`，确保子包快照不依赖父级 `wf/shared`。
- 依赖 `02_confirm_scope` 作为目标范围人工确认闸门；后续 `FOREACH` 不得绕过该阶段。
- 依赖 LGWF runtime 支持 authoring DSL `FOREACH` / runtime `subgraph.foreach`。当前仓库 bundled `vendor/lgwf-client-assist` 若仍是旧 wheel，需要先刷新后才能实际运行本 workflow。

## 状态边界

- 运行状态只允许写入 `ws/.lgwf/` 和 `ws/reports/`。
- workflow 源码树只保存 `wf/`、`tests/`、`scripts/`、入口文档和静态资源，不保存运行态 `.lgwf/`、`__pycache__/` 或临时输出。
- 目标文件写入只允许发生在 `mode=apply` 且 `state.wf_audit_fix.confirm_scope_result.decision=approve` 时；`.lgwf/scope_approval.json` 保存已批准的业务范围 context，不作为控制分支的 decision 来源。当前 item 必须同时位于 `target_manifest.json` 与 `allowed_dirs` 内。
- 每轮 Codex 修复只通过 `TARGET_FILES state.wf_audit_fix.target_files` 暴露当前 `.lgwf` 文件，不暴露整个目标仓库。
- `dry_run` 只运行 audit、记录 diagnostics 和报告，不进入写入式修复。
- package 内资源路径、`workflow.lgwf` 引用路径和文档示例路径必须使用包内相对路径，禁止绝对路径、盘符路径和 `..`。

## 产物

- `ws/.lgwf/target_manifest.json`
- `ws/.lgwf/target_scope_validation.json`
- `ws/.lgwf/scope_confirmation_context.json`
- `ws/.lgwf/scope_approval.json`
- `ws/.lgwf/foreach/upgrade_each/items/{index}/.lgwf/current_target_context.json`
- `ws/.lgwf/foreach/upgrade_each/items/{index}/.lgwf/current_target_audit.json`
- `ws/.lgwf/result_summary.json`
- `ws/reports/wf-audit-fix/report.md`

## 阶段

1. `01_collect_targets`：解析入口输入、递归展开目录内 `.lgwf` 文件、校验 `allowed_dirs` 和 `scope_mode`，生成 `target_manifest.json`。
2. `02_confirm_scope`：展示授权目标、mode、校验结果和影响范围，使用 `APPROVAL` 收集 `approve` / `reject`。
3. `FOREACH upgrade_each`：按 `state.wf_audit_fix.targets` 逐项运行 `03_upgrade_one_target`，`FAIL collect`，单个目标失败不阻塞后续目标。
4. `03_upgrade_one_target`：对当前 `.lgwf` 先做第 0 次 audit check；若 `mode=apply` 且 audit 失败，进入 `REACT repair_target MAX 3`，由 Codex 生成并执行最小修复，`OBSERVE PY` 复跑 audit check，`DECIDE PY` 根据结构化观察决定继续或退出。
5. `04_summarize_upgrade_result`：消费 `state.wf_audit_fix.target_results`，输出机器可读 summary 和中文报告。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-audit-fix\tests
$lgwfRepo = "<lgwf-repo>"
$env:PYTHONPATH = "$lgwfRepo\src"
& "$lgwfRepo\.venv\Scripts\python.exe" -m lgwf_dsl.cli audit skills\lgwf-wf-tools\workflows\wf-audit-fix\wf\workflow.lgwf
```

- 只修改文档时，至少确认文件为 UTF-8、命令路径仍与 `wf/` 和 `ws/` 语义一致。
- bundled `vendor/lgwf-client-assist` 必须刷新到支持 `FOREACH`、`RUN_WORKFLOW` 源 workflow root 解析和 `REACT OBSERVE PY` 后，再使用 facade 标准 audit / run 命令。

## 禁止事项

- 不得把本 workflow 注册为独立 Codex skill。
- 不得读取或修改未进入 manifest 的文件。
- 不得在 `dry_run` 下写入目标文件。
- 不得绕过 `02_confirm_scope` 的人工确认直接进入 `FOREACH`。
- 不得把 `reject` 路由成 `FAIL_ALL`，必须允许进入总结阶段。
- 不得把阶段私有逻辑塞进根 `wf/workflow.lgwf`。
- 不得在子 workflow 目录下继续创建孙级 `workflow.lgwf`。
- 不得在源码树写入 `.lgwf/`、`__pycache__/` 或占位运行产物。
