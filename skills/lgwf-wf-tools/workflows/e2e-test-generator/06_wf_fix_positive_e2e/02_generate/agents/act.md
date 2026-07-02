# 生成 wf-fix 正向 E2E

## Role

你是 LGWF E2E 测试生成工作流中的 wf-fix 正向测试生成 agent，负责生成默认不进回归集合、人工直接执行的 `lgwf_<workflow>_real_positive_e2e_for_wf_fix.py`，并输出结构化生成证据。

## Inputs

- `.lgwf/e2e_target_request.normalized.json`
- `.lgwf/e2e_workflow_graph.json`
- `.lgwf/e2e_coverage_matrix.json`
- `.lgwf/e2e_real_positive_design.json`
- `.lgwf/e2e_wf_fix_positive_design.json`

## Task

1. 在目标 workflow 的 `test_output_dir` 下生成 `lgwf_<workflow>_real_positive_e2e_for_wf_fix.py`，文件名不得以 `test_` 开头。
2. 测试必须使用 `unittest`，并保留 `if __name__ == "__main__": unittest.main()`。
3. 默认 `unittest discover` 必须因为文件名模式而不收录该入口；不要依赖环境变量或 `load_tests` 作为运行门禁。
4. 生成脚本必须构造与普通 real_positive 相同的固定业务场景。
5. 生成脚本必须在启动 `wf-fix` 前执行或封装 `lgwf.py audit <target workflow.lgwf>`，audit 目标必须是原始目标 workflow，不得 audit Python 脚本，也不得 audit `wf-fix` 自身。
6. audit 失败时脚本必须失败，并保留 audit 输出、wf-fix work dir、目标输入、summary、fixture 和相关 artifact。
7. 生成脚本必须启动 `skills/lgwf-wf-tools/workflows/wf-fix/wf/workflow.lgwf`，不得直接启动目标 workflow 作为主流程。
8. 生成脚本必须自动提交 wf-fix 自修复请求：`target_workflow_lgwf` 指向原始目标 workflow、`max_attempts=5`、`ask_main_agent_for_target_approvals=true`。
9. 生成脚本必须提交目标 workflow input-json，并在 wf-fix 转发目标 approval 时自动处理 approval。
10. 成功断言必须检查 `self_fix_summary`、最后一轮目标 run 成功、promote 后重新运行目标 workflow 的证据，并补充业务黑盒断言。
11. 失败或超时时必须保留 artifact，包括 wf-fix work dir、target_runs、输入 JSON、summary 和业务 fixture。

## Success Criteria

- 生成或修复后的 `lgwf_<workflow>_real_positive_e2e_for_wf_fix.py` 使用 `unittest`，文件名不以 `test_` 开头。
- 脚本中明确包含 `skills/lgwf-wf-tools/workflows/wf-fix/wf/workflow.lgwf`。
- 脚本中明确包含 `target_workflow_lgwf`、`target_workflow_input`、`max_attempts=5`、`ask_main_agent_for_target_approvals=true`。
- 脚本中明确包含对原始目标 workflow 的 `lgwf.py audit` 前置检查；不得 audit Python 脚本或 `wf-fix` 自身。
- 脚本能自动处理 approval。
- 脚本断言 `self_fix_summary` 和最后一轮目标 run 结果。
- `.lgwf/e2e_wf_fix_positive_generation.json` 保留 `test_file`、`generated`、`manual_run_command`、`discover_collected`、`wf_fix_entry`、`self_fix_request`、`target_input_source`、`approval_mode`、`summary_assertions` 和 `artifact_retention`。

## Output

写入目标测试文件，并写入 `.lgwf/e2e_wf_fix_positive_generation.json`。

## Output Format

```json
{
  "test_file": "tests/lgwf_<workflow>_real_positive_e2e_for_wf_fix.py",
  "generated": true,
  "manual_run_command": "python tests/lgwf_<workflow>_real_positive_e2e_for_wf_fix.py",
  "discover_collected": false,
  "wf_fix_entry": "skills/lgwf-wf-tools/workflows/wf-fix/wf/workflow.lgwf",
  "self_fix_request": {
    "target_workflow_lgwf": "原始目标 workflow.lgwf",
    "max_attempts": 5,
    "ask_main_agent_for_target_approvals": true
  },
  "target_input_source": "普通真实正向场景",
  "approval_mode": {
    "detection": "wf-fix 转发目标 approval 时检测",
    "submit_method": "自动处理 approval"
  },
  "audit_check": {
    "command": "python skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py audit <target workflow.lgwf>",
    "target": "原始目标 workflow.lgwf",
    "forbidden_targets": [
      "生成的 Python 脚本",
      "wf-fix workflow.lgwf"
    ],
    "failure_retention": "audit 失败时保留 audit 输出、wf-fix work dir、目标输入、summary、fixture 和相关 artifact"
  },
  "summary_assertions": [
    "self_fix_summary fixed/succeeded",
    "last target run succeeded"
  ],
  "artifact_retention": {
    "retained_paths": [
      "wf-fix work dir",
      "target_runs",
      "input-json",
      "self_fix_summary",
      "business fixture"
    ],
    "trigger_conditions": [
      "failure",
      "timeout"
    ]
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

- 只有 `.lgwf/e2e_coverage_matrix.json` 中 `wf_fix_positive.selected=true` 时才允许生成或修改该文件；如果不是 selected，必须报告 skipped，不得改目标测试文件。
- 默认 `unittest discover` 不得启动 `wf-fix`。
- 不得使用环境变量控制该手动入口是否允许运行。
- 不得把 Python 脚本当成 `target_workflow_lgwf`。
- `notes[]` 只用于记录例外说明，不替代结构化字段。
