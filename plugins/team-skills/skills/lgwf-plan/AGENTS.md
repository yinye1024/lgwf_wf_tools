# lgwf-plan 指引

本 skill 是计划驱动的 LGWF workflow package。它用于把复杂任务拆成可确认的计划契约、验收契约，并在用户确认后按 ReAct 闭环执行。

## 约束

- 主智能体只收集输入、展示草案、提交用户确认和继续执行，不直接替代独立 Codex 生成计划或验收。
- `workflow.lgwf` 是入口；不要把 `.tmp/` 下的运行结果当作源码。
- work-dir 使用相对路径 `.tmp/<run-name>`。
- `prompt_ref`、`script_ref` 必须通过 node config 传递给 client；runtime 不读取这些文件内容。
- 计划 observe 通过前不得生成验收；验收 observe 通过前不得请求用户确认。
- 用户 approve 前不得写正式 `.lgwf/react_task_plan.json` 或 `.lgwf/react_acceptance_plan.json`。
- 执行 observe 只能按已确认验收方案评审，不得新增需求。

## 最小验证

```powershell
python tests\test_structured_contracts.py
```

