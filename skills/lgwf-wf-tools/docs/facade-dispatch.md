# Facade 派发与监控流程

本文承载 workflow 启动、继续、监控、approval、run handle 和收尾规则。场景路由见根目录 `AGENTS.md`；目标直启见 [target-run.md](target-run.md)；内部 workflow 选择见 [workflow-routing.md](workflow-routing.md)。

## Facade 初始化

初始化分三层处理，不放在内部 workflow node 里：

1. Doctor 预检层：处理任何 `/lgwf-wf-tools` facade 请求前，先运行 `python scripts/doctor_lgwf_wf_tools.py`。
2. Init 同步层：doctor 失败且存在 `assets/lgwf-client-assist.zip` 时，自动运行 `python scripts/init_lgwf_wf_tools.py`；init 后再次运行 doctor。
3. 派发前预检层：doctor 通过后，派发内部 workflow 前读取 `registry.json` 和目标 workflow `AGENTS.md`。
4. Runtime 安装层：`init` 会安装 bundled LGWF wheel；后续 `vendor/lgwf-client-assist/scripts/lgwf.py` 会按 bundled wheel hash 校验 runtime/client 模块。

内部 workflow 启动依赖 bundled `lgwf.py` 和 bundled wheel；不要新增“初始化 workflow”来安装 wheel。

## 派发执行

派发前由场景文档完成目标选择：

- 目标 workflow 直启：先按 [target-run.md](target-run.md) 解析 `workflow.lgwf` 和 `work_dir`。
- 内部 workflow：先按 [workflow-routing.md](workflow-routing.md) 选择 workflow，并按 [workflow-inputs.md](workflow-inputs.md) 准备输入。

使用本目录内置 client 启动或继续：

```powershell
$lgwfPy = "vendor/lgwf-client-assist/scripts/lgwf.py"
$inputPath = "D:/tmp/lgwf-input.json"
$inputJson = @'
{
  "key": "value"
}
'@
[System.IO.File]::WriteAllText($inputPath, $inputJson, [System.Text.UTF8Encoding]::new($false))
python $lgwfPy run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json-file $inputPath --background
python $lgwfPy status --work-dir <work_dir> --session-id <session-id>
python $lgwfPy codex token-status --work-dir <work_dir>
python $lgwfPy wait
```

PowerShell 会处理引号和转义；启动时不要把 inline JSON 直接传给 `--input-json`。即使是第一次启动，也默认使用 UTF-8 no BOM 临时 input JSON 文件。仅当 payload 是纯 ASCII 空对象时，才可把 `--input-json "{}"` 作为临时 smoke 用法。

后台启动后保存同一个 `session_id` / `pid` / `work_dir`，后续 `status`、`wait`、`approval` 和 `runs` 都围绕同一个 run handle。

## 监控循环

派发任何内部 workflow 前必须读取：

- `vendor/lgwf-client-assist/AGENTS.md`
- `vendor/lgwf-client-assist/references/agent-host-assist/guide.md`
- `vendor/lgwf-client-assist/references/agent-host-assist/cli-agent-loop.md`
- `vendor/lgwf-client-assist/references/workflow-usage.md`

本 facade 使用 `registry.json` 中的固定 `work_dir`。如果已有旧数据，按 vendor 指引让用户选择 `continue` / `resume` / `rerun`。

### Codex live token 监控

对于包含 `exec.codex_prompt` 或 ReAct Codex slot 的长任务，普通 `status` 只能说明 workflow 当前节点和最近完成节点；它可能短时间内看起来不变化。主 agent 应同时使用 live token 状态判断 Codex 子任务是否仍在工作，并把 token 消耗变化作为 Codex 节点存活心跳之一：

```powershell
python $lgwfPy codex token-status --work-dir <work_dir>
```

或直接读取：

```text
<work_dir>/.lgwf/codex/status.json
```

判断规则：

- `current_instruction_id` 变化，说明 Codex 已进入新的 instruction。
- `token_usage.total_tokens`、`input_tokens`、`output_tokens`、`reasoning_output_tokens` 或 `turn_count` 增长，说明 Codex 进程仍在产生调用或输出，可视为节点仍存活且在推进。
- `updated_at_unix` 更新，说明 live status 新鲜；若命令返回 `health.stale=true`，再结合产物、stdout/stderr 和进程状态排查。
- workflow `status` 看似停在旧节点，但 token status 已进入下一 instruction 时，以 token status 作为 Codex 子任务进度依据。
- token status 本身新鲜但 token 数长时间不增长时，不要立即判定死亡；先检查是否正在等待模型首包、工具调用、文件 I/O、approval 或外部命令返回，再看 stdout/stderr、目标产物和进程状态。

只有 token status 长时间不更新、目标产物没有写出、进程也没有结束时，才把它当作疑似卡住处理；不要因为 `status` 中 `current_node` 短时间重复就重启或 rerun。

## Approval 和 waiting_human

`waiting_human` 不是完成状态。

- 如果是 `flow.human_approval`，按 vendor main-agent ask flow 在当前对话确认并提交；展示给用户前必须套用 `workflows/01-share/approval.md` 的人工确认展示模板。
- 如果是 `AGENT_LOOP` 控制状态但没有 human request，汇报 loop reason、evidence 和 artifact 路径，等待用户决定。
- 只提交用户明确确认的 approval value。
- 凡是 `approval`、`review`、`human_choice`、`waiting_human` 或子 workflow 代理确认，都必须展示确认原因、影响范围、待确认内容、可选决策、提交值、相关产物和后续动作；不得只用一句话询问用户是否确认。
- `approval submit --value-json` 和 `review submit --value-json` 当前只支持字符串参数，不支持 value file。包含中文或复杂嵌套时，优先使用 `scripts/safe_approval_submit.py` 的 `--value-file` 或 `--value-json-base64`，由脚本转换成 ASCII-only JSON 参数后提交：

```powershell
python skills\lgwf-wf-tools\scripts\safe_approval_submit.py --kind approval --work-dir <work_dir> --request-id <request_id> --decision approve --value-file <value.json> --comment "user approved"
python skills\lgwf-wf-tools\scripts\safe_approval_submit.py --kind review --work-dir <work_dir> --request-id <request_id> --route revise --value-file <value.json> --comment "user requested edits"
```

## 收尾

完成后按 vendor run artifact 查询流程读取 summary 和 changed files，再结合目标 workflow 的 `AGENTS.md` 汇总：

- 最终状态
- 关键产物
- 变更文件
- 阻塞项
- 下一步路由建议
