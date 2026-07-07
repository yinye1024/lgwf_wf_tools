# CLI Agent Usage

本文说明 Codex 主 agent 如何使用 LGWF 暴露的 CLI 接口。这里不定义 LGWF workflow 语义；`flow.human_approval` 等能力由 workflow DSL、runtime 和 capability catalog 定义。CLI 只负责暴露本地协作接口：读取 human request、协助确认 controller payload、查询 run artifacts。这里不使用 MCP，也不依赖 Codex 私有接口。

分层边界：

1. LGWF runtime / DSL / catalog 定义 workflow 能力和运行规则。
2. `scripts/lgwf.py` 是暴露给外部 agent 的统一 facade。
3. `references/agent-host-assist/` 说明 Codex 主 agent 如何调用这些接口并维持同一个 workflow loop。

本文中的 `<skill-dir>` 指 `lgwf-client-assist` facade 根目录。Agent 统一使用 `scripts/lgwf.py`。

## Agent Host / Main Agent 代理职责

当用户让 agent 运行 LGWF workflow 时，agent 是 LGWF 的代理，不只是命令启动器：

- 用后台模式启动 workflow，避免 agent 被同步子进程占住。
- 定时读取 workflow status，并在 chat 中同步当前节点、能力、最近结果、错误或等待事项。
- 发现 `flow.human_approval` pending request 时，主 agent 不启动新窗口或 approval worker；它在当前对话读取 request、展示摘要、询问用户 approve/reject、写 controller payload 并一步提交。
- 发现 `flow.handoff` pending action 时，主 agent 不把它当作 approval，也不自动启动下游 workflow；它展示 `workflow_id`、`input_json_file`、`suggested_command` 和 `source_artifacts`，说明当前 workflow 已完成职责，并等待用户确认是否运行下一 workflow。
- Human approval 是当前 workflow loop 的一个等待状态，不是 workflow 结束。进入该状态后，主 agent 必须保留 `pid`、`work_dir`、`request_id` 并继续原 loop；不要结束成“一次性答复”，不要在用户后续回复 OK / 确认时重新执行启动前旧数据预检或提示 `rerun`。
- `AGENT_LOOP` 的 `waiting_human` 是 loop 控制状态，通常写在 `state.agent_loop.<id>.status` 或显式 `STATUS` path；它不一定对应 `.lgwf/human/*.request.json`。如果没有 human request，先向用户汇报 loop 的 `reason`、`stop_reason`、`evidence` 和 artifact 路径，再等待用户决定是否调整输入或重新运行。
- workflow 完成后读取 run summary 和 changed files，向用户汇总结果。

不要用普通同步 run 命令运行可能包含 human approval 或长时间 Codex 节点的 workflow。

## 启动 Workflow

`scripts/lgwf.py run` 会自动安装随 skill 分发的 wheel，不要求预先运行 `doctor`。长 workflow 优先使用后台模式：

启动前必须先检查 `work_dir` 是否已有旧 workflow 数据。不要直接运行后台启动命令来“顺便触发”旧数据提示；主 agent 必须先显式执行：

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json "{}" --continue-existing
```

如果 stdout 返回现有 workflow status，或包含 `phase=existing_data`、`pending_human_requests`、`latest_run`、`pid` 等字段，说明 `work_dir` 已有旧数据。此时主 agent 必须先在 chat 中问用户：

- `rerun`：清空 `<work_dir>` 下的旧内容，重新运行 workflow。
- `continue`：继续跟踪现有 workflow；这只报告或轮询现有进程状态，不从失败节点恢复。
- `resume`：使用最新 failed / stopped checkpoint 从对应节点重新执行；对应节点会重跑一次，已完成前序节点不重跑。如果没有 failed / stopped checkpoint，且进程已停止，可使用 orphaned running checkpoint 调试恢复。

用户选择 `continue` 时，保存返回的 `pid` 并进入 status 轮询；如果没有 `pid`，只汇报现有 run / pending human requests，不启动新 workflow。

用户选择 `resume` 时，后台启动命令必须追加 `--resume-existing`；如果 workflow source 已修改且用户确认要用新版 workflow 调试恢复，再追加 `--resume-allow-workflow-changed`：

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json "{}" --background --resume-existing
```

用户选择 `rerun` 时，后台启动命令必须追加 `--rerun-existing`：

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json "{}" --background --rerun-existing
```

`--rerun-existing` 会先调用随 runner 分发的 work-dir guard。非空目录只有在识别到 LGWF artifacts 后才会清理；识别失败时命令返回错误并保留目录内容。清理成功后启动新的 workflow，agent 后续跟踪新返回的 `session_id` / `pid`。

如果 workflow 正在 review 或人工确认节点等待，用户发现后续 workflow 或资源需要修复，主 agent 应先受控停止当前进程，并传入 `--work-dir` 让 runtime checkpoint 标记为 `status=stopped`：

```powershell
python <skill-dir>\scripts\lgwf.py stop --pid <pid> --work-dir <work_dir>
```

修复 workflow package 或资源后，用户确认继续时使用 `--resume-existing` 恢复同一个 run；不要用 `--rerun-existing` 重新创建 run，除非用户明确要放弃当前 run 数据。

runner 会先通过 `scripts/lgwf_env_init/work_dir_guard.py` 验证非空 `work_dir` 的 LGWF 标记。验证失败时返回退出码 2 并保留全部文件；主 agent 将错误反馈给用户，不继续启动 workflow。

只有确认 `work_dir` 没有旧数据，或用户明确选择 `rerun` 后，才能启动新 workflow：

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json "{}" --background
```

该命令会输出 JSON，其中包含 `session_id`、`session_file`、`pid`、`log_file`、`pid_file`、`workflow_json` 和 `work_dir`。agent 优先保存 `session_id`；兼容旧流程时也保存 `pid`，后续用它查询状态或停止 workflow。

当 status 返回 `phase=completed` 或 `running=false` 时，workflow 已结束；后续通过 run artifact 查询命令读取 summary 和 changed files。

查询当前状态：

```powershell
python <skill-dir>\scripts\lgwf.py status --pid <pid> --work-dir <work_dir>
python <skill-dir>\scripts\lgwf.py status --work-dir <work_dir> --session-id <session_id>
```

`status` JSON 包含：

- `running`
- `phase`
- `current_node`
- `current_capability`
- `last_result`
- `last_error`
- `human_request_id`
- `pending_human_requests`
- `latest_run`
- `log_tail`
- `main_agent_status`

Agent display rule: `status` JSON is machine input, not user-facing output. Prefer `main_agent_status` when present because it is the stable main-agent control-plane view. Do not print the full JSON, `log_tail`, or `last_result` in heartbeat updates. For each poll, summarize in 3-5 short lines:

```text
状态：运行中
当前节点：mma_class_rules__class_design__observe（exec.codex_prompt）
正在等待：Codex 节点完成
最近完成：mma_class_rules__class_design__act，用时 13分32秒，成功
下一步：继续轮询，不重启 workflow
```

If `phase=waiting_human`, the summary must say it is waiting for user approval and include the `human_request_id`; then follow the main-agent ask flow below. If `phase=waiting_handoff`, the summary must say the current workflow is handing off to the next workflow and include the `pending_action.request_id` and `pending_action.workflow_id`. If the same `last_result` repeats across polls, do not print it again.

停止后台 workflow：

```powershell
python <skill-dir>\scripts\lgwf.py stop --pid <pid>
```

同步频率要求：agent 自己保留 workflow loop；每次需要等待下一轮查询时，调用 LGWF client 暴露的固定休眠入口：

```powershell
python <skill-dir>\scripts\lgwf.py wait
```

休眠返回后，再调用已有 status 查询：

```powershell
python <skill-dir>\scripts\lgwf.py status --pid <pid> --work-dir <work_dir>
```

进入 `waiting_human` 后立即向用户同步，不继续自动 approve。

进入 `waiting_review` 后立即向用户同步，不把 `revise` 当成 approval reject。

进入 `waiting_handoff` 后立即向用户同步，不自动运行 `suggested_command`。

重要：`waiting_human` / `waiting_review` 不是退出条件。进入该状态后，主 agent 不能把当前 workflow 视为已完成，也不能在后续用户消息中重新启动 workflow。后续用户消息如果是对当前 approval 或 review 的确认，应直接回到当前 `pid` / `work_dir` / `request_id`，读取 controller payload 并继续提交流程。

## Human Approval Main-Agent Ask Flow

当 workflow 按自身 DSL 运行到 `flow.human_approval` 节点时，LGWF 会写入 `.lgwf/human/<request_id>.request.json`，等待 `.lgwf/human/<request_id>.response.json`。Codex 主 agent 在当前对话中完成确认并一步提交，不启动新窗口或 approval worker。

当 workflow 进入 `flow.human_approval` 节点时，stderr/progress 会出现类似事件：

```text
[workflow] node waiting id=confirm_params capability=flow.human_approval
[workflow] human approval pending request_id=human-xxxx
```

workflow 进程会在该节点阻塞等待 response 文件。主 agent 通过 `--status-pid` 的 `human_request_id`、`pending_human_requests[].request_id` 或 progress 中的 `request_id` 定位请求。

主 agent 编排要求：

1. 轮询 status，发现 `phase=waiting_human` 或 `current_capability=flow.human_approval`。
2. 取得 `request_id`。
3. 读取 request：

```powershell
python <skill-dir>\scripts\lgwf.py approval get --work-dir <work_dir> --request-id <request_id>
```

4. 在当前对话展示 `prompt` 和 `context` 摘要，明确说明正在确认什么、approve 后会把什么 `value` 写入 workflow、reject 后 workflow 会失败。
5. 询问用户选择 `approve` 或 `reject`。不要把模糊回复当成确认。
6. 用户 approve 时，默认使用 request 的 `context` 作为 `value`；如果用户明确修改字段，则用修改后的 JSON value。
7. 用户 reject 时，必须写入用户给出的拒绝原因作为 `comment`。
8. 优先使用 main-agent 高层提交命令。approve 必须传入 `--value-json`，reject 必须传入 `--comment`：

```powershell
python <skill-dir>\scripts\lgwf.py approval submit --work-dir <work_dir> --request-id <request_id> --decision approve --value-json "{...}" --comment "user approved"
python <skill-dir>\scripts\lgwf.py approval submit --work-dir <work_dir> --request-id <request_id> --decision reject --comment "user rejected"
```

9. 如需兼容底层流程，写入 controller payload，`created_by` 固定为 `main_agent_ask`，`created_at` 为当前 UTC ISO 8601 时间：

```powershell
python <skill-dir>\scripts\lgwf.py approval controller-write --work-dir <work_dir> --request-id <request_id> --payload-json "{...}"
```

10. 使用底层流程时，写入 payload 后立即一步提交：

```powershell
python <skill-dir>\scripts\lgwf.py approval controller-submit --work-dir <work_dir> --request-id <request_id> --final-user-confirmed true
```

11. 提交后立即执行一次 `scripts/lgwf.py status` 查询原 workflow；如果仍在运行，下一轮 loop 先调用 `scripts/lgwf.py wait`。

主 agent loop 状态机：

```text
running workflow
  -> status phase=waiting_human
  -> get request
  -> show prompt/context summary and ask approve/reject in current chat
  -> user approve: write payload created_by=main_agent_ask with value
  -> user reject: write payload created_by=main_agent_ask with comment
  -> submit payload immediately
  -> continue polling the same pid
```

主 agent 禁止事项：

- 不要启动新的交互窗口或 approval worker。
- 不要调用 `respond-human-request`。
- 不要直接写 `.response.json`。
- 不要伪造用户确认。
- 不要在用户没有明确 approve/reject 时写 payload。
- 不要在当前 workflow 仍有 `pid` / `request_id` 时建议 `rerun`，除非用户明确说要从头重跑。

`submit-human-controller-payload` 会把 `.controller_payload.json` 转换为 `.response.json`，并写入 `submitted_via="controller_payload"`、`final_user_confirmed=true` 和原始 `controller_payload` 审计字段。`reject` 会让 workflow 失败并写入 failed run artifacts。

## Human Review Main-Agent Ask Flow

当 workflow 运行到 `flow.human_review` 节点时，LGWF 复用 `.lgwf/human/<request_id>.request.json` 通道，但 request 会包含 `kind="human_review"`、固定 `options=["approve","revise","reject"]`、完整 `review_context_json`、`display_template.kind="review_json_v1"` 和 `revise_requires_full_json=true`。主 agent status 会返回 `phase=waiting_review`、`pending_action.type="human_review"`、`agent_instruction="ask_user_review_choice"`。

处理要求：

1. 按 `display_template` 展示 `prompt`、完整 `review_context_json` 和三个固定选项 `approve`、`revise`、`reject`；不要只展示摘要后让用户凭空修改。
2. 询问用户选择一个 option。`approve` 表示当前 JSON 可继续，`revise` 表示需要主 agent 先改 JSON 再重新评审，`reject` 表示当前 workflow 不应继续。
3. 用户选择 `revise` 时，主 agent 必须结合用户修改要求和当前 `review_context_json`，生成完整的更新后 JSON object；不要提交局部 patch、数组或自由文本，也不要提交 `decision=reject`。
4. 优先使用高层命令：

```powershell
python <skill-dir>\scripts\lgwf.py review submit --work-dir <work_dir> --request-id <request_id> --route revise --value-json "{...complete updated context object...}" --comment "user requested edits"
```

提交后继续轮询同一个 workflow。`REVIEW` 节点会把 route 写入 `RESULT.route`，并用该 route 匹配 `FLOW ... WHEN "<route>" THEN ...`。如果 `revise` route 回到同一个 `REVIEW` 节点，workflow 会再次进入 `waiting_review`，request 会暴露更新后的 `review_context_json`；主 agent 必须再次按同一模板展示完整 JSON，并再次询问用户选择 `approve` / `revise` / `reject`。

## Agent Handoff Main-Agent Flow

当 workflow 运行到 `flow.handoff` 节点时，LGWF 会写入 `.lgwf/handoff/<request_id>.pending.json`，并在 `main_agent_status.pending_action` 暴露同一对象。这个事件表示当前 workflow 的职责已完成，下一步应由主 agent 在用户确认后接续另一个 workflow。

主 agent 编排要求：

1. 轮询 status，发现 `phase=waiting_handoff` 或 `pending_action.type="agent_handoff"`。
2. 在当前对话展示 `workflow_id`、`input_json_file`、`suggested_command` 和关键 `source_artifacts`。
3. 明确说明 `auto_execute=false`，不会自动启动下游 workflow。
4. 如果 `requires_user_confirmation=true`，必须等待用户明确确认后才运行 `suggested_command` 或等价的 `scripts/lgwf.py run ...` 命令。
5. 用户确认后，把下游 workflow 作为新的 workflow run 跟踪；不要把 handoff 当成 human approval，也不要写 `.lgwf/human/*.response.json`。

主 agent 禁止事项：

- 不要把 `agent_handoff` 显示成 approve/reject 审批。
- 不要在用户未确认时启动下游 workflow。
- 不要修改 handoff pending file 来模拟确认。
- 不要把上游 workflow 重新运行来“继续 handoff”。

低层兼容 API：

```powershell
python <skill-dir>\scripts\lgwf.py approval respond --work-dir <work_dir> --request-id <request_id> --caller human_controller --approval-token <token> --response-json "{...}"
```

该命令只保留给已有 external human controller 使用。普通用户和主 agent 都不要手写或推荐该命令；`<token>` 不得通过 prompt、日志、repo 文件或 agent 可读 shell environment 暴露给 LLM/agent。

## Run Artifact Query

workflow 完成后，列出最近 run：

```powershell
python <skill-dir>\scripts\lgwf.py runs list --work-dir <work_dir> --limit 1
```

读取 run summary：

```powershell
python <skill-dir>\scripts\lgwf.py runs summary --work-dir <work_dir> --run-id <run_id>
```

读取 changed files manifest：

```powershell
python <skill-dir>\scripts\lgwf.py runs changed --work-dir <work_dir> --run-id <run_id>
```

## Human Approval Main-Agent Flow

As of 2026-06-03, an LLM/agent must not write `.response.json` directly and must not call `respond-human-request` as the normal path.

当前统一流程允许主 agent 读取 request 正文，在当前对话取得用户 approve/reject 后写 `created_by="main_agent_ask"` 的 controller payload，并通过 `submit-human-controller-payload` 一步提交。

这个流程的边界：主 agent 可以作为用户确认的代理，但最终 response 仍只能由 controller payload 提交流程生成；不要绕过审计文件直接写 `.response.json`。
