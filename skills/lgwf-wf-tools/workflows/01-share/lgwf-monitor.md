# LGWF 监控规则

后台启动后必须保存同一个 `session_id`、`pid` 和 `work_dir`，后续 `status`、`wait`、`approval` 和 `runs` 都围绕同一个 run handle。

```powershell
python vendor/lgwf-client-assist/scripts/lgwf.py status --work-dir <work_dir> --session-id <session-id>
python vendor/lgwf-client-assist/scripts/lgwf.py codex token-status --work-dir <work_dir>
python vendor/lgwf-client-assist/scripts/lgwf.py wait
```

## Codex 节点进度判断

当 `status` 长时间停在 `exec.codex_prompt`、`subgraph.react` 的 reason/act/observe，或显示的 `current_node` 看起来没有变化时，不要只凭 workflow status 判断“卡住”。主 agent 应同时读取 Codex live token 状态：

```powershell
python vendor/lgwf-client-assist/scripts/lgwf.py codex token-status --work-dir <work_dir>
```

该命令读取 `<work_dir>/.lgwf/codex/status.json`。重点看：

- `current_instruction_id`：当前 Codex instruction，例如 `design_prompt_upgrade__act:codex_prompt`。
- `token_usage.total_tokens`：如果轮询之间持续增加，说明 Codex 子任务仍在工作。
- `turn_count`：同一 instruction 内完成的 Codex turn 数。
- `updated_at_unix` / `health.seconds_since_update`：判断 live status 是否新鲜。
- `status`：`running` 表示当前 Codex instruction 仍在执行；`completed` 表示最近一个 instruction 已结束。

推荐判断顺序：

1. 先用 `status` 判断 workflow 当前节点、是否 `waiting_human`、是否完成或失败。
2. 如果当前能力是 Codex 节点，再用 `codex token-status` 判断 token 是否在增长；`total_tokens=0` 或 `seconds_since_update` 增大只能说明 live status 暂未刷新，不能单独作为失败依据。
3. 如果 workflow status 看似停留在旧节点，但 `current_instruction_id` 已变化、token 增长、track dir 的 `stdout.txt` 继续写入，或 process log 出现节点推进记录，应按仍在推进处理。
4. Codex 节点未达到自身 `timeout_seconds` 前，主 agent 不得自行判定失败，不得自行 `stop`、`rerun` 或跳过节点；只能把疑似无进展的证据提醒用户，并等待用户决定。
5. 只有出现明确终态证据时才可判失败：process log 出现 `node failed`、track dir `metadata.json` 中 `exit_code` 非 0、`timed_out=true`，或后台进程已退出且没有节点完成记录和目标产物。
6. 排查疑似卡住时必须同时检查 workflow `status`、后台 process log、当前 Codex track dir 的 `metadata.json` / `stdout.txt` / `stderr.txt`，以及后台 `pid` 是否仍存在。

如果已有旧数据，按 vendor 指引让用户选择 `continue`、`resume` 或 `rerun`。
