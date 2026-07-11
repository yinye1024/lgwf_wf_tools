# wf-maintenance-gate

## 模块定位

- 模块类型：`lgwf_workflow_package`。
- 本目录是 `skills/lgwf-wf-tools/registry.json` 派发的内部 workflow package，不是独立 Codex skill。
- 目标：对 `lgwf-wf-tools` 仓库维护改动执行变更归档、影响分类、验证计划确认、已确认验证执行和结果汇总。

## 入口

- registry id：`wf-maintenance-gate`
- workflow 入口：`wf/workflow.lgwf`
- work dir：`ws/`
- 输入契约：`entry_contract.json`
- 启动命令：

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py run --workflow-lgwf skills/lgwf-wf-tools\workflows\wf-maintenance-gate\wf\workflow.lgwf --work-dir skills\lgwf-wf-tools\workflows\wf-maintenance-gate\ws --input-json-file <utf8-json-file>
```

## 依赖

- 依赖 `skills/lgwf-wf-tools/vendor/lgwf-client-assist/` 提供 LGWF runtime。
- 依赖 `skills/lgwf-wf-tools/scripts/doctor_lgwf_wf_tools.py`、打包脚本和目标 workflow 自身测试目录作为可选验证对象。
- 依赖 git 工作树事实、`skills/lgwf-wf-tools/registry.json` 和仓库源码路径做影响分类。

## 状态边界

- 运行态只允许写入 `ws/.lgwf/` 与 `ws/reports/`。
- workflow 源码固定在 `wf/`；不得向源码树写入 `.lgwf`、`.tmp` 或其他运行时文件。
- 所有 workflow/resource 引用必须使用包内相对路径；不得使用绝对路径或 `..`。

## 产物

- `ws/.lgwf/maintenance_gate_request.json`
- `ws/.lgwf/change_context.json`
- `ws/.lgwf/impact_classification.json`
- `ws/.lgwf/verification_plan_proposal.json`
- `ws/.lgwf/verification_plan.json`
- `ws/.lgwf/verification_results.json`
- `ws/.lgwf/failure_routes.json`
- `ws/.lgwf/maintenance_gate_summary.json`
- `ws/reports/wf-maintenance-gate/report.md`

## 验证

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-maintenance-gate\wf\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-maintenance-gate\tests
```

## 禁止事项

- 不自动修复失败、不自动重试、不自动启动下游 workflow。
- 不绕过 `04_confirm_verification_plan` 的人工 REVIEW。
- 不把 package smoke、pre-release 或覆盖现有 zip 变成默认自动行为。
- 不修改 `vendor/`、`registry.json` 或当前维护请求之外的源码。
