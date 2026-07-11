# plan 工作流

本目录是 `lgwf-wf-tools` 内部的通用计划驱动任务 workflow。它按以下契约闭环运行：

1. 生成计划草案。
2. 基于计划草案生成验收草案。
3. 由用户一次性确认计划与验收契约。
4. 按 task 顺序执行、评审、记录并路由。

执行阶段中，单个 task 的 ReAct 循环达到最大轮次后会进入人工决策解析节点。用户可以选择继续修复、接受当前结果、跳过当前 task 或停止后续执行；workflow 会先把该决策落到 `.lgwf/react_task_plan.json` 和 `.lgwf/react_task_route.json`，再回到统一路由节点继续分发，避免出现“工作流结束但任务仍阻塞”的状态。

## 计划安全契约

任务输入必须声明 `target_type`，取值为 `create_artifact`、`modify_artifact`、`execute_process`、`analyze`、`fix` 或 `review`。计划草案的 `summary.target_type` 应与任务输入一致；每个 task 必须声明：

- `task_role`：`implementation_action`、`validation_action`、`generated_artifact_behavior` 或 `human_decision`。
- `execution_subject`：当前执行主体，例如 `current_lgwf_plan_run`、`target_artifact_files` 或 `generated_artifact_runtime`。
- `produced_artifacts`：当前 task 会创建、修改或验证的文件、目录、代码、配置、文档或报告。

当 `target_type=create_artifact` 时，当前执行计划不得包含 `task_role=generated_artifact_behavior`，也不得把 `execution_subject` 指向未来运行时。目标 workflow、skill、插件或文档包未来运行时的业务节点，只能作为待生成 artifact 的内容出现，不能作为本次 `lgwf-plan` run 的 task 执行。该检查会在计划生成决策和用户 approve 后正式落盘前各执行一次。

## 启动

从 facade 根目录 `skills\lgwf-wf-tools` 运行：

```powershell
python workflows\plan\scripts\cleanup_lgwf_plan_runtime.py --package-root workflows\plan\ws
python scripts\run_skill_workflow.py --workflow-id plan --input-json-file D:\tmp\lgwf-plan-input.json --background
```

`wf/` 是 workflow package root，`ws/` 是固定 work-dir。两者保持同级，避免运行产物被 `lgwf-client-assist` 复制进 workflow snapshot。

入口 JSON 必须包含 `react_task_request`，并至少声明 `objective`、`request`、`target_type`，以及 `analysis_target_files` 或 `analysis_target_dirs` 之一；完整字段以 `entry_contract.json` 为准。

## 核心产物

- `.lgwf/react_task_request.json`
- `.lgwf/react_task_plan_proposal.json`
- `.lgwf/react_acceptance_proposal.json`
- `.lgwf/react_task_plan.json`
- `.lgwf/react_acceptance_plan.json`
- `.lgwf/react_task_context.json`
- `.lgwf/react_task_result.json`
- `.lgwf/react_task_history.json`
- `reports/react-task/react_task_report.md`

## 测试

默认端到端和脚本流测试可以直接运行：

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\plan\tests
```

本次计划安全契约的最小验证命令：

```powershell
python -m pytest skills/lgwf-wf-tools/workflows/plan/tests/test_lgwf_plan_script_flow.py
python -m pytest skills/lgwf-wf-tools/workflows/plan/tests/test_structured_contracts.py -k "plan_generation_spec or confirmation_template or confirmation_context"
```

真实 Codex 端到端测试默认跳过，需要显式开启：

```powershell
$env:LGWF_PLAN_REAL_CODEX_E2E='1'
$env:LGWF_PLAN_REAL_CODEX_E2E_TIMEOUT_SECONDS='5400'
python skills\lgwf-wf-tools\workflows\plan\tests\test_lgwf_plan_real_positive_e2e.py
```

如果需要保留真实端到端运行目录用于排查，设置 `$env:LGWF_PLAN_REAL_CODEX_E2E_KEEP_WORKDIR='1'`。测试会把产物复制到 `tests\.tmp`。
