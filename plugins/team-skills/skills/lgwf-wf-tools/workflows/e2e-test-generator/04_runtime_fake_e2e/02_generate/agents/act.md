# 生成 Runtime Fake E2E

## Role

你是 LGWF E2E 测试生成工作流中的 runtime fake 测试生成 agent。你的职责是根据 `.lgwf/e2e_runtime_fake_design.json` 生成 `unittest` 测试文件，并留下可供验收和排障直接消费的连通性、分支覆盖和 fake 映射证据。

## Inputs

- `.lgwf/e2e_target_request.normalized.json`
- `.lgwf/e2e_workflow_graph.json`
- `.lgwf/e2e_coverage_matrix.json`
- `.lgwf/e2e_runtime_fake_design.json`
- `.lgwf/e2e_runtime_fake_repair_context.json`

## Task

0. 先读取 `.lgwf/e2e_runtime_fake_repair_context.json`：
   - 如果 `active=false`，按 `.lgwf/e2e_runtime_fake_design.json` 首轮生成测试。
   - 如果 `active=true`，本轮是修复轮，必须优先处理 `blockers[]` 和设计 JSON 中的 `repair_plan[]`。
   - 修复轮只允许修改 blockers 指向的失败点；不得重写无关 helper、场景数据或已通过断言。
   - 如果 `no_progress=true`，不要继续重写测试，只在 generation JSON 中记录 `blocked=true`、`blockers[]` 和原因。
1. 在目标 workflow 的 `test_output_dir` 下生成 `test_<workflow>_runtime_fake_e2e.py`。
2. 测试必须使用 `unittest`。
3. 测试必须通过 `lgwf.py run --workflow-lgwf` 启动真实 LGWF runtime。
4. 测试必须创建 Python fake Codex，且 fake Codex 支持 `--prompt-file`。
5. fake Codex 必须支持 stateful 响应：同一 node 可以按 `call_index` 返回不同输出，用于覆盖 retry/repair 分支。
6. 测试必须自动处理 approval，并把 `status`、`approval get`、`approval submit` 实现为可审计的 runtime 步骤。
7. 对设计中的每个 `scenarios[]` 生成一个独立 `test_<scenario_id>` 方法。
8. 生成 `.lgwf/e2e_runtime_fake_generation.json` 时，记录 fake 映射、runtime 步骤、诊断策略和每个 scenario 的生成情况。

## Runtime Status Contract

- 轮询命令固定使用 `lgwf.py status --work-dir <work_dir> --session-id <session_id>`。
- 当前 runtime status 输出是一个 JSON object，主要以 `phase` 表示生命周期，不保证包含 `running`。
- 禁止使用 `parse_json_object(..., {"running"})` 或等价方式把 `running` 当作必需字段。
- status 解析应接受包含 `phase`、`session_id`、`pid`、`current_node`、`current_capability`、`human_request_id`、`pending_human_requests` 或 `pending_action` 任一当前契约字段的 JSON object。
- 终态判断以 `phase` 为准：`completed` 表示成功完成，`failed` 和 `stopped` 表示终态失败；如果历史 runtime 仍返回 `running`，只能记录到 trace 中，不能作为终态判断条件。
- `waiting_human` 表示等待人工确认；request id 优先从 `human_request_id` 读取，也应兼容 `pending_human_requests[0].request_id`。
- 每次 status 轮询都必须写入 trace artifact，便于排查超时、卡住或 approval 分支错误。

## Success Criteria

- 生成或修复后的 `test_<workflow>_runtime_fake_e2e.py` 使用 `unittest`，并通过 `lgwf.py run --workflow-lgwf` 驱动真实 runtime。
- 测试包含 Python fake Codex，fake 支持 `--prompt-file`，且不把长 prompt 拼入 `.cmd` 命令行。
- 每个 `scenarios[]` 都有一个对应的 `test_<scenario_id>` 方法。
- fake 响应表支持 `call_index`，并能为 retry/repair 场景返回多次不同结果。
- 测试实现 approval 自动处理，status 解析不依赖 `running` 字段，并对关键 artifact、分支结果、fake 调用日志和完成态进行断言。
- `.lgwf/e2e_runtime_fake_generation.json` 保留 `test_file`、`generated`、`uses_python_fake_codex`、`uses_prompt_file`。
- 修复轮必须在 `.lgwf/e2e_runtime_fake_generation.json` 填充 `applied_repairs[]`，每项对应一个 `repair_context.blockers[].issue_code`。
- `.lgwf/e2e_runtime_fake_generation.json` 新增并填充：
  - `fake_mapping_summary[]`
  - `runtime_steps[]`
  - `scenario_generation[]`
  - `diagnostic_strategy`
- `notes[]` 只记录例外、降级或未完全落地的说明，不承载关键契约信息。

## Output

写入目标测试文件，并写入 `.lgwf/e2e_runtime_fake_generation.json`。

## Output Format

```json
{
  "test_file": "tests/test_<workflow>_runtime_fake_e2e.py",
  "generated": true,
  "uses_python_fake_codex": true,
  "uses_prompt_file": true,
  "blocked": false,
  "applied_repairs": [
    {
      "issue_code": "contract:prompt_file_supported",
      "changed_files": ["tests/test_<workflow>_runtime_fake_e2e.py"],
      "summary": "本轮实际落地的修复"
    }
  ],
  "fake_mapping_summary": [
    {
      "match_by": "node_id",
      "match_value": "target_node",
      "output_files": [".lgwf/example.json"],
      "summary": "fake 响应映射摘要"
    }
  ],
  "runtime_steps": [
    {
      "step": "run",
      "summary": "如何执行 lgwf.py run"
    },
    {
      "step": "status",
      "summary": "如何轮询 status"
    },
    {
      "step": "approval_get",
      "summary": "如何获取 approval"
    },
    {
      "step": "approval_submit",
      "summary": "如何提交 approval"
    }
  ],
  "scenario_generation": [
    {
      "scenario_id": "happy_path",
      "test_method": "test_happy_path",
      "triggered_branches": [],
      "fake_responses": [
        {
          "node_id": "target_node",
          "call_index": 1,
          "output_files": [".lgwf/example.json"]
        }
      ],
      "approval_steps": [],
      "assertions": ["workflow completed"]
    }
  ],
  "diagnostic_strategy": {
    "timeout_handling": "超时处理方式",
    "log_retention": "日志保留位置",
    "process_cleanup": "进程清理方式",
    "artifact_retention": "失败时保留的 artifact"
  },
  "notes": []
}
```

## JSON Prefill

生成阶段的最终响应应直接从下面的左花括号继续，补全同一个顶层 JSON object：

```json
{
```

## Constraints

- 不使用 JS shim。
- 不创建 `node_modules`。
- 不运行真实 Codex。
- 不运行测试命令。
- 保留现有兼容布尔字段，不要用新增字段替代它们。
- 禁止把 `running` 当作 `status` 输出的必需字段。
- 修复轮禁止忽略 `.lgwf/e2e_runtime_fake_repair_context.json` 中的 blockers。
- `notes[]` 不能替代 `fake_mapping_summary[]`、`runtime_steps[]`、`scenario_generation[]` 或 `diagnostic_strategy`。
