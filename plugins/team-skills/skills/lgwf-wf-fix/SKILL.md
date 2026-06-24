---
name: lgwf-wf-fix
description: 通过修复循环运行一个 LGWF workflow。用于用户提供目标 workflow.lgwf、一次性收集该 workflow 的启动输入、运行目标 workflow、检查 LGWF 日志和产物、在 candidate workspace 中修复目标 workflow source、验证后 promote 到真实目标目录、反复重跑直到成功，并可按启动确认开关代理目标 workflow 的人工确认。
---

# LGWF Workflow Fix

将本 skill 作为 `lgwf_wf_fix` 面向 Codex 的入口。skill 本身只负责入口说明；实际修复逻辑在 `wf/workflow.lgwf` 中。

## 启动

始终通过 LGWF facade 启动：

```powershell
python <lgwf-client-assist>/scripts/lgwf.py run --workflow-lgwf plugins\team-skills\skills\lgwf-wf-fix\wf\workflow.lgwf --work-dir plugins\team-skills\skills\lgwf-wf-fix\ws --input-json "{}" --background
```

workflow 会在第一个 approval step 中询问 `target_workflow_lgwf`、`max_attempts` 和 `ask_main_agent_for_target_approvals`。不要通过启动时的 `input-json` 传入这些字段；用户确认后的值会持久化到 `.lgwf/self_fix_request_input.json`。

固定 work dir 是 `plugins\team-skills\skills\lgwf-wf-fix\ws`。如果其中已经存在历史 LGWF 数据，按 `lgwf-client-assist` 的 continue/rerun 流程处理，不要盲目启动第二个 run。

## 交互约定

workflow 分两层收集输入：

1. workflow 先让用户确认 workflow-fix 任务：要修复哪个 `workflow.lgwf`、最大重试次数，以及是否代理目标 workflow 的 `APPROVAL`。确认结果持久化到 `.lgwf/self_fix_request_input.json`。
2. workflow 再分析目标 workflow，向用户询问目标 workflow 的业务启动 JSON，并持久化到 `.lgwf/target_workflow_input.json`。

`.lgwf/target_workflow_input.json` 保存后，后续每次目标 workflow 尝试都必须复用这个 JSON object 作为目标 workflow 的 `--input-json`。
`ask_main_agent_for_target_approvals` 默认是 `false`。只有用户在第一个 approval 明确设为 `true` 时，workflow-fix 才会把目标 workflow 的 `APPROVAL` 转发到当前对话等待确认；否则目标 workflow 等待确认时 fix 会阻塞结束并提示人工接管。

## 运行处理

- 使用 `lgwf.py status` 和 `lgwf.py wait` 持续跟踪同一个 `lgwf_wf_fix` run。
- 当 `lgwf_wf_fix` 询问目标启动参数时，展示生成的 contract，并要求用户提供一个 JSON object。
- 当目标 workflow 进入 `APPROVAL` 且 `ask_main_agent_for_target_approvals=true` 时，workflow-fix workflow 会把该请求转发到当前对话。在当前对话中询问用户 approve 或 reject，然后继续同一个 run。
- 当目标 workflow 进入 `APPROVAL` 且 `ask_main_agent_for_target_approvals=false` 时，不要自动提交目标 approval；按 final report 中的阻塞原因交给人工接管。
- 不要自动 approve 目标 workflow 的 approval 请求。
- 提交任何 approval JSON、`--input-json` 或 `--value-json` 时必须保护 UTF-8 语义：不要把包含中文或其他非 ASCII 字符的 JSON 直接写进 PowerShell/cmd 命令文本。优先使用 UTF-8 文件或 stdin；如果 CLI 只能接收参数，参数值必须使用 ASCII-only JSON（例如 `\uXXXX` 转义）并由 Python `subprocess` 以 argv 传入。
- 提交后必须读回对应 `.lgwf/human/*.response.json` 或目标 `.lgwf/*.json`，确认中文没有变成 `?` / `????`。一旦发现编码损坏，停止当前 run，修正提交方式后重跑；不要基于损坏输入继续诊断目标 workflow。
- 修复节点只修改 `.lgwf/target_repair/current/workspace/candidate` 中的 candidate source；验证通过后由 promote gate 把允许的变更写回真实目标目录。

## 输出

在固定 work dir 下查看这些产物：

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
- `reports/lgwf-wf-fix/final_report.md`
