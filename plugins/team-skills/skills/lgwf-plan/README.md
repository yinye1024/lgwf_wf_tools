# lgwf-plan

`lgwf-plan` 是通用计划驱动任务 workflow。它按以下契约闭环运行：

1. 生成计划草案。
2. 基于计划草案生成验收草案。
3. 由用户一次性确认计划与验收契约。
4. 按 task 顺序执行、评审、记录并路由。

执行阶段中，单个 task 的 ReAct 循环达到最大轮次后会进入人工决策解析节点。用户可以选择继续修复、接受当前结果、跳过当前 task 或停止后续执行；workflow 会先把该决策落到 `.lgwf/react_task_plan.json` 和 `.lgwf/react_task_route.json`，再回到统一路由节点继续分发，避免出现“工作流结束但任务仍阻塞”的状态。

## 启动

在本目录运行：

```powershell
python scripts/cleanup_lgwf_plan_runtime.py --package-root .
python D:\allen\github\lgwf\wf_fix\skills\lgwf-client-assist\scripts\lgwf.py run --workflow-lgwf workflow.lgwf --work-dir .tmp\<run-name> --input-json "{}"
```

`<run-name>` 使用任务语义生成短横线名称。不要把 work-dir 指向父级仓库，也不要把历史 `.tmp` 运行目录当成模板源码。

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
python -m unittest discover plugins\team-skills\skills\lgwf-plan\tests
```

真实 Codex 端到端测试默认跳过，需要显式开启：

```powershell
$env:LGWF_PLAN_REAL_CODEX_E2E='1'
$env:LGWF_PLAN_REAL_CODEX_E2E_TIMEOUT_SECONDS='5400'
python plugins\team-skills\skills\lgwf-plan\tests\test_lgwf_plan_real_positive_e2e.py
```

如果需要保留真实端到端运行目录用于排查，设置 `$env:LGWF_PLAN_REAL_CODEX_E2E_KEEP_WORKDIR='1'`。测试会把产物复制到 `tests\.tmp`。

