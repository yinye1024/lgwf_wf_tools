# lgwf-plan

`lgwf-plan` 是通用计划驱动任务 workflow。它按以下契约闭环运行：

1. 生成计划草案。
2. 基于计划草案生成验收草案。
3. 由用户一次性确认计划与验收契约。
4. 按 task 顺序执行、评审、记录并路由。

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

