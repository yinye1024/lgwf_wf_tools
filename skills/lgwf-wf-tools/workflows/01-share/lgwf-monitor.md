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
2. 如果当前能力是 Codex 节点，再用 `codex token-status` 判断 token 是否在增长。
3. 如果 workflow status 看似停留在旧节点，但 `current_instruction_id` 已变化或 token 增长，应按 token status 判断为仍在推进。
4. 只有在 token status 长时间不更新、产物没有落盘、进程仍未结束时，才按运行异常排查，不要提前重启 workflow。

如果已有旧数据，按 vendor 指引让用户选择 `continue`、`resume` 或 `rerun`。
