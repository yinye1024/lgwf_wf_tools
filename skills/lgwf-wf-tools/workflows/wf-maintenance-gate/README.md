# wf-maintenance-gate

`wf-maintenance-gate` 用于在 `lgwf-wf-tools` 仓库内执行维护前 gate。它把“改了哪些文件”转换成“需要确认和执行哪些验证”，并输出可读报告与机器可读 summary。

## 模块定位

- 模块类型：`lgwf_workflow_package`。
- 本目录是 `skills/lgwf-wf-tools/registry.json` 派发的内部 workflow package，不是独立 Codex skill。
- 目标：对 `lgwf-wf-tools` 仓库维护改动执行变更归档、影响分类、验证计划确认、已确认验证执行和结果汇总。

## 入口

- registry id：`wf-maintenance-gate`
- workflow root：`wf/workflow.lgwf`
- work dir：`ws/`
- 输入契约：`entry_contract.json`
- 启动命令：

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py run --workflow-lgwf skills\lgwf-wf-tools\workflows\wf-maintenance-gate\wf\workflow.lgwf --work-dir skills\lgwf-wf-tools\workflows\wf-maintenance-gate\ws --input-json-file <utf8-json-file>
```

## 输入

入口对象固定为 `maintenance_gate_request`，常用字段包括：

- `scope`：维护范围说明，默认 `auto`
- `changed_files`：显式提供的仓库相对路径列表；为空时由 git 自动收集
- `target_workflows`：显式限定的 workflow id 列表
- `intent`：如 `maintenance`、`package_ready`
- `verification_level`：`light`、`standard`、`full`
- `allow_deep_doctor`
- `allow_workflow_tests`
- `allow_pre_release`
- `allow_package_smoke`
- `output_zip`

## 依赖

- 依赖 `skills/lgwf-wf-tools/vendor/lgwf-client-assist/` 提供 LGWF runtime 与 authoring audit。
- 依赖 `skills/lgwf-wf-tools/registry.json`、git 工作树事实和仓库源码路径做影响分类。
- 依赖 `skills/lgwf-wf-tools/scripts/doctor_lgwf_wf_tools.py`、目标 workflow 测试目录和打包脚本作为可选验证对象。
- 依赖 `wf/shared/scripts/maintenance_gate_common.py` 统一维护影响分类、验证命令模板和失败路由规则。

## 阶段

1. `01_collect_change_context`：归一化请求并收集变更上下文。
2. `02_classify_impact`：分类影响面、受影响 workflow 与风险等级。
3. `03_plan_verification`：生成待确认验证计划草案。
4. `04_confirm_verification_plan`：唯一强制人工 REVIEW 点。
5. `05_run_verification`：按已确认计划执行验证并记录事实。
6. `06_summarize_gate_result`：汇总 summary 与中文报告。

## 状态边界

- workflow 源码固定在 `wf/`，运行态固定写入 `ws/.lgwf/` 与 `ws/reports/`。
- `05_run_verification` 允许执行 `04_confirm_verification_plan` 已确认的命令；若命令会写入 `.local/doctor/`、`.local/self-improve/`、`skills/lgwf-wf-tools/output/` 等目录，这些写入属于已确认 `write_effects` 的受控外部副作用，不等同于 workflow 自身固定运行态目录。
- 不得向 `wf/` 源码树写入 `.lgwf`、`.tmp` 或其他运行态文件；所有 workflow/resource 引用必须使用包内相对路径，禁止绝对路径和 `..`。

## 产物

- `ws/.lgwf/maintenance_gate_request.json`
- `ws/.lgwf/change_context.json`
- `ws/.lgwf/impact_classification.json`
- `ws/.lgwf/verification_plan_proposal.json`
- `ws/.lgwf/verification_plan_approval.json`
- `ws/.lgwf/verification_plan.json`
- `ws/.lgwf/verification_results.json`
- `ws/.lgwf/maintenance_gate_summary.json`
- `ws/.lgwf/failure_routes.json`
- `ws/reports/wf-maintenance-gate/report.md`

## 非目标

- 不自动修复 workflow、prompt 或 DSL 问题。
- 不自动执行 pre-release、zip 覆盖或正式发布。
- 不自动更新 facade registry 或 vendor。

## 验证

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-maintenance-gate\wf\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-maintenance-gate\tests
```

## 禁止事项

- 不绕过 `04_confirm_verification_plan` 的人工 REVIEW；所有验证命令及其 `write_effects` 都必须先确认。
- 不自动修复失败、不自动重试、不自动启动下游 workflow。
- 不把 package smoke、pre-release 或覆盖现有 zip 变成默认自动行为。
- 不修改 `vendor/`、`registry.json` 或当前维护请求之外的源码。
