# lgwf_wf_self_fix

`lgwf_wf_self_fix` 用于运行并自修复一个目标 LGWF workflow。它会先分析目标 workflow 的启动参数契约，向用户收集一次目标 workflow 的业务 `input-json`，之后每轮运行都复用这份参数。

## 运行方式

通过外层 Codex skill `lgwf-wf-self-fix` 启动本 workflow。固定 work dir 为：

```text
plugins/team-skills/skills/lgwf-wf-self-fix/ws
```

启动参数至少包含：

```json
{
  "target_workflow_lgwf": "<workflow A>/workflow.lgwf",
  "max_attempts": 5
}
```

`target_workflow_lgwf` 必填，`max_attempts` 可选，默认值为 `5`。

## 输出

主要运行产物写入 work dir：

- `.lgwf/self_fix_request.json`
- `.lgwf/self_fix_target.json`
- `.lgwf/target_input_contract.json`
- `.lgwf/target_workflow_input.json`
- `.lgwf/target_runs/attempt-*/`
- `.lgwf/target_failure_review.json`
- `.lgwf/self_fix_history.json`
- `reports/lgwf-wf-self-fix/final_report.md`

目标 workflow 运行中进入 `APPROVAL` 时，本 workflow 会代理该确认请求并在当前对话中等待用户 approve 或 reject。
