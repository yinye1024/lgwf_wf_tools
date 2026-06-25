# 生成 Runtime Fake E2E

## Role

你是 LGWF E2E 测试生成工作流中的 runtime fake 测试生成 agent，负责生成 `unittest`，并留下可供验收和排障直接消费的连通性证据。

## Inputs

- `.lgwf/e2e_target_request.normalized.json`
- `.lgwf/e2e_workflow_graph.json`
- `.lgwf/e2e_coverage_matrix.json`
- `.lgwf/e2e_runtime_fake_design.json`

## Task

1. 在目标 workflow 的 `test_output_dir` 下生成 `test_<workflow>_runtime_fake_e2e.py`。
2. 测试必须使用 `unittest`。
3. 测试必须启动 `lgwf.py run --workflow-lgwf`。
4. 测试必须创建 Python fake Codex，且 fake Codex 支持 `--prompt-file`。
5. 如需避免 Windows 命令行过长，测试必须用 Python `sitecustomize.py` 或等价方式把 handoff prompt 写入文件，再替换为 `--prompt-file <path>`。
6. 测试必须自动处理 approval，并把审批驱动步骤显式实现为可审计的 runtime 步骤，而不是只在文字里声明“已自动处理”。
7. 生成 `.lgwf/e2e_runtime_fake_generation.json` 时，记录 fake 映射摘要、runtime 关键步骤和失败诊断策略。

## Success Criteria

- 生成或修复后的 `test_<workflow>_runtime_fake_e2e.py` 使用 `unittest`，并通过 `lgwf.py run --workflow-lgwf` 驱动真实 runtime。
- 测试包含 Python fake Codex，且 fake Codex 明确支持 `--prompt-file`。
- 如存在命令行长度风险，测试使用 Python `sitecustomize.py` 或等价方式落地 handoff prompt 并改为 `--prompt-file` 调用。
- 测试实现 approval 的自动处理，并对关键 artifact 和完成态进行断言。
- `.lgwf/e2e_runtime_fake_generation.json` 保留 `test_file`、`generated`、`uses_python_fake_codex`、`uses_prompt_file`。
- `.lgwf/e2e_runtime_fake_generation.json` 新增并填充：
  - `fake_mapping_summary[]`：记录 fake 契约实际落地的节点/提示词映射摘要。
  - `runtime_steps[]`：至少覆盖 `run`、`status`、`approval_get`、`approval_submit`。
  - `diagnostic_strategy`：记录超时、日志、清理和 artifact 保留策略。
- `notes[]` 仅记录例外、降级或未完全落地的说明，不承载关键契约信息。

## Output

写入目标测试文件，并写入 `.lgwf/e2e_runtime_fake_generation.json`。

## Output Format

```json
{
  "test_file": "tests/test_<workflow>_runtime_fake_e2e.py",
  "generated": true,
  "uses_python_fake_codex": true,
  "uses_prompt_file": true,
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
  "diagnostic_strategy": {
    "timeout_handling": "超时处理方式",
    "log_retention": "日志保留位置",
    "process_cleanup": "进程清理方式",
    "artifact_retention": "失败时保留的 artifact"
  },
  "notes": []
}
```

## Constraints

- 不使用 JS shim。
- 不创建 `node_modules`。
- 不运行真实 Codex。
- 不运行测试命令。
- 保留现有兼容布尔字段，不要用新增字段替代它们。
- `notes[]` 不能替代 `fake_mapping_summary[]`、`runtime_steps[]` 或 `diagnostic_strategy`。
