# wf-audit-fix

`wf-audit-fix` 是独立 Codex skill，用于对一个已存在的 LGWF workflow package 执行静态 `audit -> candidate 修复 -> promote -> 真实目录复检` 闭环。内嵌 LGWF workflow 入口固定为 `wf/workflow.lgwf`。

## 输入

运行时至少提供：

```json
{
  "target_workflow_lgwf": "D:/path/to/workflow.lgwf",
  "max_attempts": 5
}
```

- `target_workflow_lgwf`：目标 `workflow.lgwf` 路径
- `max_attempts`：可选整数，默认 `5`

## 输出

- 真实目录首轮 `audit` 结果与结构化诊断
- candidate 修复尝试日志与通过快照
- promote 结果与真实目录复检结果
- 最终 `result_summary`

## 结构

- `SKILL.md`：Codex skill 入口
- `AGENTS.md`：模块协作指引
- `wf/workflow.lgwf`：根薄编排，只引用四个第一层子 workflow
- `wf/02_confirm_requirements/`：输入归一化与路径护栏
- `wf/04_confirm_business_flow/`：真实目录首轮 audit 闸门
- `wf/07_confirm_step_designs/`：candidate 修复与复检循环
- `wf/09_summarize_create_result/`：promote、真实目录复检与摘要
- `wf/docs/steps/`：已批准步骤设计文档副本

## 运行边界

- 只修静态 DSL 或 audit 问题
- 不运行目标 workflow
- 不处理目标 workflow approval
- 运行态只写入 `ws/.lgwf`
- 不通过 `lgwf-wf-tools/registry.json` 派发

## 最小验证

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\wf-audit-fix\wf\workflow.lgwf
python -m unittest discover skills\wf-audit-fix\tests
```
