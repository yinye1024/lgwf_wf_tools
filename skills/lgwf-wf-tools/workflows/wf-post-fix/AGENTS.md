# LGWF Workflow Post Fix 指引

本目录是 `lgwf-wf-tools` facade 下的内部 workflow package，职责是对一个已有 LGWF workflow 做综合后处理：prompt 基础修复、prompt 设计升级、E2E 测试生成，以及生成后测试入口的可选执行。它不是独立 Codex skill，不得单独注册；外部只能通过 `lgwf-wf-tools` 根目录 `SKILL.md` 和 `registry.json` 派发到本目录的 `wf/workflow.lgwf`。

## 模块契约

- 模块类型：`lgwf_workflow_package`。
- 执行前必须读取 `../01-share/module-contract.md`、`../01-share/registry-contract.md`、`../01-share/lgwf-dispatch.md`、`../01-share/lgwf-monitor.md`、`../01-share/approval.md` 和 `../01-share/artifacts.md`。
- 组合调用下游 workflow 时，不得绕过下游模块自己的自包含契约和 approval 边界。

## 业务边界

- 本 workflow 只编排已有 workflow，不替代 `wf-prompt-fix`、`wf-prompt-upgrade`、`e2e-test-generator` 的内部职责。
- 默认每个阶段运行前都要向用户解释该阶段作用、可能影响和跳过后果，并请求 `run | skip | auto | stop` 决策；用户选择 `stop` 时，由当前子 workflow 直接 `FAIL_ALL` 终止并向父 workflow 传播失败。
- 用户选择 `auto` 后，只自动进入允许自动的阶段：`wf-prompt-fix`、`wf-prompt-upgrade`、`e2e-test-generator`、`script_flow_e2e`、`runtime_fake_e2e`。
- `real_positive_e2e` 和 `wf_fix_positive_e2e` 即使处于 `auto` 也必须再次请求用户确认。
- 子 workflow 自己的 approval 永远不能被 `auto` 绕过；主 agent 必须按 `workflows/01-share/approval.md` 的人工确认展示模板展示子 workflow 原始确认上下文并等待明确确认。

## 输入契约

启动时通过 `--input-json` 传入目标 workflow 信息：

```json
{
  "post_fix_target": {
    "target_workflow_lgwf": "D:/example/workflow.lgwf",
    "target_package_root": "D:/example",
    "target_dirs": ["D:/example"],
    "mode": "manual"
  }
}
```

- `target_workflow_lgwf` 必填，可以是绝对路径。
- `target_package_root` 可省略，默认使用 `target_workflow_lgwf` 所在目录。
- `target_dirs` 可省略，默认使用 `target_package_root`。
- `mode` 可省略，默认 `manual`；只允许 `manual` 或 `auto`。

入口阶段会先请求人工确认目标 JSON，再标准化并写入 `.lgwf/post_fix_target.json`。涉及中文或复杂 JSON 时，优先写入 UTF-8 文件再传入。

## 运行流程

根 `wf/workflow.lgwf` 只负责编排阶段顺序，不承接子 workflow 的 `stop` 路由；子 workflow 内部的 `stop` 会直接 `FAIL_ALL` 并击穿整个运行：

1. `prepare_target`：确认并标准化目标信息。
2. `route_prompt_fix`：解释 `wf-prompt-fix`，按用户决策运行、跳过、进入 auto 或停止。
3. `prompt_fix`：通过 `RUN_WORKFLOW` 调用 `workflows/wf-prompt-fix/wf/workflow.lgwf`。
4. `route_prompt_upgrade`：解释 `wf-prompt-upgrade` 并处理阶段决策。
5. `prompt_upgrade`：通过 `RUN_WORKFLOW` 调用 `workflows/wf-prompt-upgrade/wf/workflow.lgwf`。
6. `route_e2e_generate`：解释 `e2e-test-generator` 并处理阶段决策。
7. `e2e_generate`：通过 `RUN_WORKFLOW` 调用 `workflows/e2e-test-generator/workflow.lgwf`。
8. `route_script_flow_e2e`、`route_runtime_fake_e2e`、`route_real_positive_e2e`、`route_wf_fix_positive_e2e`：确认并执行或跳过生成后的测试入口；任一阶段选择 `stop` 会在该子 workflow 内直接 `FAIL_ALL`。
9. `finish`：仅在所有阶段正常完成或跳过后汇总阶段状态、跳过原因、生成测试、测试结果和后续建议。

## 固定输出

```text
.lgwf/post_fix_target.json
.lgwf/post_fix_decisions.json
.lgwf/post_fix_stage_results.json
.lgwf/post_fix_generated_tests.json
.lgwf/post_fix_summary.json
reports/wf-post-fix/report.json
reports/wf-post-fix/report.md
```

## 使用方式

本 workflow 应由 `lgwf-wf-tools` facade 派发：

```powershell
$lgwfPy = "skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy run --workflow-lgwf skills\lgwf-wf-tools\workflows\wf-post-fix\wf\workflow.lgwf --work-dir skills\lgwf-wf-tools\workflows\wf-post-fix\ws --input-json <json> --background
```

固定 `work_dir` 如果已有历史 LGWF 数据，先按 facade 的 continue/rerun 流程询问用户，不要直接启动第二个 run。

## 本 package 自检

修改本 workflow package 后，至少执行：

```powershell
$lgwfPy = "skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy audit skills\lgwf-wf-tools\workflows\wf-post-fix\wf\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-post-fix\tests
```
