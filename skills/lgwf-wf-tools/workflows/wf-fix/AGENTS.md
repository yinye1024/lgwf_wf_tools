# LGWF Workflow Fix 指引

本目录是 `lgwf-wf-tools` facade 下的内部 workflow package，职责是运行一个目标 LGWF workflow，观察失败或阻塞原因，并在候选目录中自动修复目标 workflow package，验证通过后再 promote 回真实目标目录。它不是独立 Codex skill，不得单独注册；外部只能通过 `lgwf-wf-tools` 根目录 `SKILL.md` 和 `registry.json` 派发到本目录的 `wf/workflow.lgwf`。

## 业务职责

- 接收用户指定的目标 `workflow.lgwf`，确认最大修复次数和目标 approval 是否转发到当前主 agent。
- 分析目标 workflow 的启动参数契约，向用户收集一次目标 workflow 业务 `input-json`，后续每轮运行复用这份输入。
- 启动目标 workflow，持续观察其运行状态、输出产物、失败信息和人工确认请求。
- 当目标 workflow 失败或输出不满足契约时，在 `.lgwf/target_repair/current/workspace/candidate` 中准备候选工作区。
- 通过 `AGENT_LOOP repair_target` 执行诊断、修复计划、应用修改、候选验证和复核，最多按用户确认的 `max_attempts` 进行多轮目标运行和修复。
- 只有候选验证通过并且路由决定 `promote` 时，才把允许的变更写回真实目标目录，并记录本轮修复历史。
- 输出最终报告，说明目标 workflow 是否已修复、是否仍阻塞、修改了哪些文件、后续需要人工处理什么。

本 workflow 处理的是“目标 workflow 运行失败或无法完成”的修复闭环。它可以修改目标 workflow package 中的 DSL、prompt、script 或相关资源，但不负责系统性 prompt 质量升级，也不负责单独生成 E2E 测试。prompt 基础规范问题优先路由到 `wf-prompt-fix`；prompt 设计升级优先路由到 `wf-prompt-upgrade`；测试生成优先路由到 `e2e-test-generator`。

## 适用场景

- 目标 workflow 已有 `workflow.lgwf`，但运行失败、卡在可诊断状态，或最终输出不符合预期。
- 用户希望由 Agent 反复运行目标 workflow，基于真实失败证据修复目标 package。
- 目标 workflow 可能包含 `APPROVAL` 节点，需要决定是否把目标 approval 转发到当前主 agent 对话。
- 修复需要先落在隔离候选目录中，验证后再写回真实目标目录。

不适合的场景：

- 目标目录还没有可解析的 `workflow.lgwf`。
- 用户只想审计 prompt 引用、上下文和基础规范，不需要运行目标 workflow。
- 用户只想提升 prompt 策略、角色职责或输出质量标准，不需要基于失败运行修复。
- 用户只想生成测试骨架，而不是修复目标 workflow 当前失败。

## 输入契约

启动本 workflow 时使用空 JSON object。不要通过启动时的 `--input-json` 预填修复参数；workflow 会在第一个 approval step 中询问并确认：

```json
{
  "target_workflow_lgwf": "D:/example/workflow.lgwf",
  "max_attempts": 5,
  "ask_main_agent_for_target_approvals": false
}
```

- `target_workflow_lgwf` 必填，可以是用户提供的绝对路径，也可以是相对当前仓库的路径。
- `max_attempts` 可选，默认 `5`，表示目标 workflow 运行失败后最多允许多少轮修复尝试。
- `ask_main_agent_for_target_approvals` 可选，默认 `false`。只有设为 `true` 时，目标 workflow 自己的 `APPROVAL` 请求才会被转发到当前主 agent 对话。

用户确认后的修复请求会持久化到 work dir 的 `.lgwf/self_fix_request_input.json`，标准化目标信息会写入 `.lgwf/self_fix_request.json` 和 `.lgwf/self_fix_target.json`。

随后 workflow 会分析目标 `workflow.lgwf` 的启动参数契约，生成 `.lgwf/target_input_contract.json`，再通过 `collect_target_workflow_input` approval 要求用户提交目标 workflow 的业务 `input-json`。该业务输入会持久化到 `.lgwf/target_workflow_input.json`，后续每一轮目标运行都复用它。

## 业务流程

1. `prepare_self_fix_request_context`：准备自修复请求确认上下文。
2. `confirm_self_fix_request`：让用户确认目标 workflow、最大尝试次数和目标 approval 转发策略。
3. `prepare_target`：解析并标准化目标 workflow 路径、目标 package root、允许修复的目录和运行上下文。
4. `analyze_target_input_contract`：读取目标 workflow package，由 Codex 分析目标启动输入契约。
5. `prepare_input_collection_context`：整理目标输入契约，准备业务输入收集上下文。
6. `collect_target_workflow_input`：请求用户提交目标 workflow 的业务 `input-json`。
7. `validate_target_workflow_input`：校验业务输入能满足目标 workflow 启动契约。
8. `repair_target_loop`：运行目标 workflow，观察结果，并根据状态路由到继续观察、approval 转发、修复或完成。
9. `summarize_self_fix`：汇总所有目标运行、修复尝试、promote 结果和最终状态。

`repair_target_loop` 的核心分支如下：

- `run_target_workflow` 启动目标 workflow，并把每轮运行记录写入 `.lgwf/target_runs/attempt-*/`。
- `observe_target_run` 观察目标 run；如果仍在运行则继续观察，如果需要目标 approval 则进入 `proxy_target_approval`，如果失败或不满足契约则进入修复，如果成功则完成。
- `proxy_target_approval` 只在 `ask_main_agent_for_target_approvals=true` 时向当前对话请求用户确认；之后由 `submit_target_approval` 写回目标 run 并继续观察。
- `prepare_repair_agent_loop` 准备候选修复工作区和当前失败观察材料。
- `repair_target` 执行诊断、方案、应用、验证和复核；修复只允许落在 candidate workspace 中。
- `promote_repair_candidate` 在候选验证通过后，把允许的变更写回真实目标目录。
- `record_fix_attempt` 记录本轮修复，再重新运行目标 workflow 验证真实目录是否已修复。
- `finish_self_fix` 在成功、用户阻塞、达到上限或不可修复时结束当前修复循环。

## 交互处理

- 使用 `lgwf.py status` 和 `lgwf.py wait` 持续跟踪同一个 `lgwf_wf_fix` run，不要在未处理旧 run 状态时直接启动第二个 run。
- 当本 workflow 询问自修复请求时，向用户展示目标字段和默认值，只提交用户明确确认的 JSON object。
- 当本 workflow 询问目标 workflow 业务输入时，展示 `.lgwf/target_input_contract.json` 的契约摘要，要求用户提供目标 workflow 需要的 JSON object。
- 当目标 workflow 进入 `APPROVAL` 且 `ask_main_agent_for_target_approvals=true` 时，在当前对话中询问用户 approve 或 reject，然后继续同一个 run。
- 当目标 workflow 进入 `APPROVAL` 且 `ask_main_agent_for_target_approvals=false` 时，不要自动提交目标 approval；让 workflow 以阻塞状态结束，并在最终报告中说明需要人工接管目标 workflow。
- 不要自动 approve 目标 workflow 的 approval 请求。

提交任何 approval JSON、`--input-json` 或 `--value-json` 时必须保护 UTF-8 语义：不要把包含中文或其他非 ASCII 字符的 JSON 直接写进 PowerShell/cmd 命令文本。优先使用 UTF-8 文件或 stdin；如果 CLI 只能接收参数，参数值必须使用 ASCII-only JSON（例如 `\uXXXX` 转义）并由 Python `subprocess` 以 argv 传入。提交后必须读回对应 `.lgwf/human/*.response.json` 或目标 `.lgwf/*.json`，确认中文没有变成 `?` / `????`。一旦发现编码损坏，停止当前 run，修正提交方式后重跑；不要基于损坏输入继续诊断目标 workflow。

## 修复与 Promote 边界

- 修复节点只修改 `.lgwf/target_repair/current/workspace/candidate` 中的 candidate source；不要直接修改真实目标目录。
- 候选验证 workflow 会运行 `verify_repair_candidate`，必要时进入 `review_repair_candidate` 由 Codex 复核变更、验证结果和风险。
- 只有 `route_after_repair_agent_loop` 返回 `promote` 时，才允许执行 `promote_repair_candidate`。
- promote 后必须重新运行目标 workflow；不能只因为候选区验证通过就宣称真实目标已修复。
- 达到 `max_attempts`、遇到用户 approval 阻塞、候选验证失败且无法继续、或目标输入不满足契约时，应结束并在 final report 中说明原因。

## 固定输出

固定 work dir 使用 registry 中的 `workflows/wf-fix/ws`。主要产物包括：

```text
.lgwf/self_fix_request_input.json
.lgwf/self_fix_request.json
.lgwf/self_fix_target.json
.lgwf/target_input_contract.json
.lgwf/target_workflow_input.json
.lgwf/target_approval_decision.json
.lgwf/target_runs/attempt-*/
.lgwf/target_repair/current/*.json
.lgwf/target_repair/current/workspace/candidate/
.lgwf/target_repair/iterations/*/
.lgwf/target_repair/report.json
.lgwf/self_fix_summary.json
.lgwf/self_fix_history.json
reports/lgwf-wf-tools/final_report.md
```

其中 `target_approval_decision.json` 只在目标 approval 被转发并由用户确认时出现；`target_repair/current` 和 `target_repair/iterations` 只在发生修复尝试时有完整内容。

## 使用方式

本 workflow 应由 `lgwf-wf-tools` facade 派发：

1. 读取 facade 根目录 `registry.json` 中 `wf-fix` 的 `workflow_lgwf`、`work_dir` 和 `agents_md`。
2. 读取本文件，确认启动时使用空 JSON object，并准备处理后续 approval。
3. 使用 bundled client 启动并持续跟进同一个 run：

```powershell
$lgwfPy = "skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy run --workflow-lgwf skills\lgwf-wf-tools\workflows\wf-fix\wf\workflow.lgwf --work-dir skills\lgwf-wf-tools\workflows\wf-fix\ws --input-json "{}" --background
python $lgwfPy status --session-id <session-id>
python $lgwfPy wait --session-id <session-id>
```

固定 `work_dir` 如果已有历史 LGWF 数据，先按 facade 的 continue/rerun 流程询问用户，不要直接覆盖或混用旧 run。缺少 bundled `lgwf-client-assist` 时必须直接失败并报告，不要 fallback 到用户 `.codex` 目录的外部 skill。

workflow package 内部 `SCRIPT`、`PROMPT`、`PROMPT_REF`、`CONTEXT workflow` 和 `STEP ... WORKFLOW` 路径保持相对路径；用户提供的 `target_workflow_lgwf` 可以是绝对路径。运行时必须通过 `workflow.json` 或编译后的 runtime IR 执行，不要把 Markdown 说明材料当作 workflow 入口。

## 本 package 自检

修改本 workflow package 后，至少执行：

```powershell
$lgwfPy = "skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy audit skills\lgwf-wf-tools\workflows\wf-fix\wf\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-fix\tests
```

如果只修改本说明文件，可以不运行完整 workflow，但应确认 UTF-8 内容可读、路径示例仍与当前目录结构一致。
