# lgwf_wf_fix

`lgwf_wf_fix` 用于运行并修复一个目标 LGWF workflow。它会先分析目标 workflow 的启动参数契约，向用户收集一次目标 workflow 的业务 `input-json`，之后每轮运行都复用这份参数。

## 运行方式

通过外层 Codex skill `lgwf-wf-agent` 启动本 workflow。固定 work dir 为：

```text
plugins/team-skills/skills/lgwf-wf-agent/workflows/wf-fix/ws
```

启动时使用空 `input-json`。workflow 会在第一个 `APPROVAL` 节点中询问 fix 参数：

```json
{
  "target_workflow_lgwf": "<workflow A>/workflow.lgwf",
  "max_attempts": 5,
  "ask_main_agent_for_target_approvals": false
}
```

`target_workflow_lgwf` 必填，`max_attempts` 可选，默认值为 `5`。`ask_main_agent_for_target_approvals` 可选，默认值为 `false`；只有设为 `true` 时，本 workflow 才会把目标 workflow 的 `APPROVAL` 转发到主 agent 对话中确认。

确认结果会持久化到 `.lgwf/self_fix_request_input.json`。后续 workflow 会分析目标 workflow 的启动参数契约，再单独收集一次目标 workflow 的业务 `input-json`，并保存为 `.lgwf/target_workflow_input.json`。

## 输出

主要运行产物写入 work dir：

- `.lgwf/self_fix_request.json`
- `.lgwf/self_fix_target.json`
- `.lgwf/target_input_contract.json`
- `.lgwf/target_workflow_input.json`
- `.lgwf/target_runs/attempt-*/`
- `.lgwf/target_repair/current/*.json`
- `.lgwf/target_repair/iterations/*/`
- `.lgwf/target_repair/report.json`
- `.lgwf/self_fix_summary.json`
- `.lgwf/self_fix_history.json`
- `reports/lgwf-wf-agent/final_report.md`

目标 workflow 运行中进入 `APPROVAL` 时，只有 `ask_main_agent_for_target_approvals=true` 才会转发该确认请求并在当前对话中等待用户 approve 或 reject。默认 `false` 时，fix 会以阻塞状态结束并提示人工接管目标 workflow。

主 agent 提交任何 approval payload 时必须保护 UTF-8 语义。不要把包含中文的 JSON 直接写入 PowerShell/cmd 命令文本或直接传给 `--value-json`。统一使用 skill 根目录的 `scripts/safe_approval_submit.py`，通过 UTF-8 `--value-file`、ASCII-only `--value-json-ascii` 或 UTF-8 base64 传值；提交后读回 `.lgwf/human/*.response.json` 验证内容没有被替换成 `?`。
