# 启动 wf-create-fast

你正在接手 `wf-convert` 的后续动作。按下面步骤启动 `wf-create-fast`：

1. 先对当前 `agent_handoff` pending action 提交 `handoff submit` ack，记录主 agent 已接收。
2. 从当前 handoff context 读取 `input_json_file`、`workflow_id` 和 `suggested_command`。
3. 确认用户允许启动下游 workflow 后执行 `suggested_command`，或等价执行：

```powershell
python skills\lgwf-wf-tools\scripts\run_skill_workflow.py --workflow-id wf-create-fast --input-json-file <input_json_file>
```

4. 启动后按 `wf-create-fast` 的运行状态继续监控和处理人工确认。
