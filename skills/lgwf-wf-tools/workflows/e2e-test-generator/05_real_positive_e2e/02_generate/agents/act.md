# 生成真实 Codex 正向 E2E

## Role

你是 LGWF E2E 测试生成工作流中的真实正向测试生成 agent，负责生成默认不进回归集合、人工直接执行的真实正向手动入口，并输出场景实现证据卡。

## Inputs

- `.lgwf/e2e_target_request.normalized.json`
- `.lgwf/e2e_workflow_graph.json`
- `.lgwf/e2e_coverage_matrix.json`
- `.lgwf/e2e_real_positive_design.json`

## Task

1. 在目标 workflow 的 `test_output_dir` 下生成 `lgwf_<workflow>_real_positive_e2e.py`，文件名不得以 `test_` 开头。
2. 测试必须使用 `unittest`。
3. 默认 `unittest discover` 必须因为文件名模式而不收录该真实 Codex 入口；不要依赖环境变量或 `load_tests` 作为运行门禁。
4. 测试必须保留 `if __name__ == "__main__": unittest.main()`，人工验收时可直接执行该文件。
5. 测试必须在启动真实目标 workflow 前执行或封装 `lgwf.py audit <target workflow.lgwf>`，audit 目标必须是原始目标 `workflow.lgwf`。
6. audit 失败时脚本必须失败，并保留 audit 输出、work dir、fixture 和相关 artifact，便于人工诊断。
7. 测试必须启动真实 `lgwf.py run --workflow-lgwf`。
8. 测试必须自动处理 approval。
9. 测试必须创建业务 fixture，并在结束后做黑盒断言。
10. 失败或超时时必须保留运行 artifact。
11. 生成 `.lgwf/e2e_real_positive_generation.json` 时，记录场景映射、fixture 摘要、approval 模式、audit check 摘要、黑盒断言摘要和 artifact retention。

## Success Criteria

- 生成或修复后的 `lgwf_<workflow>_real_positive_e2e.py` 使用 `unittest`，文件名不以 `test_` 开头，使默认 `unittest discover` 不收录。
- 人工验收时直接执行测试文件即可运行真实正向链路，不要求设置真实 Codex 环境变量开关。
- 测试在真实运行前执行 `lgwf.py audit <target workflow.lgwf>`，audit 失败时终止并保留 audit 输出与 artifact。
- 测试通过 `lgwf.py run --workflow-lgwf` 启动真实 runtime，并自动处理 approval。
- 测试创建业务 fixture、执行最终黑盒断言，并在失败或超时时保留运行 artifact。
- `.lgwf/e2e_real_positive_generation.json` 保留 `test_file`、`generated`、`manual_run_command`、`discover_collected`、`default_runs_real_codex`。
- `.lgwf/e2e_real_positive_generation.json` 新增并填充：
  - `scenario_mapping`：记录场景到测试方法的映射。
  - `fixture_summary`：记录 fixture 入口、创建路径和清理/保留边界。
  - `approval_mode`：记录 approval 检测与提交方式。
  - `black_box_assertions[]`：记录业务结果断言摘要。
  - `artifact_retention`：记录保留目录与触发条件。
- `notes[]` 只用于记录例外说明，不替代结构化字段。

## Output

写入目标测试文件，并写入 `.lgwf/e2e_real_positive_generation.json`。

## Output Format

```json
{
  "test_file": "tests/lgwf_<workflow>_real_positive_e2e.py",
  "generated": true,
  "manual_run_command": "python tests/lgwf_<workflow>_real_positive_e2e.py",
  "discover_collected": false,
  "default_runs_real_codex": false,
  "scenario_mapping": {
    "scenario_id": "real_positive_minimal_flow",
    "test_method": "test_real_positive_minimal_flow",
    "fixture_entry": "主要 fixture 入口或构造函数"
  },
  "fixture_summary": {
    "created_paths": [
      "测试创建的目录或文件"
    ],
    "cleanup_strategy": "成功后的清理方式",
    "failure_retention_boundary": "失败时保留哪些内容"
  },
  "approval_mode": {
    "detection": "如何检测 approval",
    "submit_method": "如何自动提交 approval"
  },
  "audit_check": {
    "command": "python skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py audit <target workflow.lgwf>",
    "target": "原始目标 workflow.lgwf",
    "failure_retention": "audit 失败时保留 audit 输出、work dir、fixture 和相关 artifact"
  },
  "black_box_assertions": [
    {
      "assertion_id": "assert_output_exists",
      "observable_output": "可观察业务结果",
      "expected_value": "预期值"
    }
  ],
  "artifact_retention": {
    "retained_paths": [
      "失败或超时时保留的目录"
    ],
    "trigger_conditions": [
      "failure",
      "timeout"
    ],
    "default_cleanup": "成功时的默认清理行为"
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

- 只有 `.lgwf/e2e_coverage_matrix.json` 中 `real_positive.selected=true` 时才允许生成或修改该文件；如果不是 selected，必须报告 skipped，不得改目标测试文件。
- 默认 `unittest discover` 不得启动真实 Codex。
- 不得使用环境变量控制该手动入口是否允许运行；直接执行文件即运行真实正向链路。
- 不生成 fake Codex。
- 不承担全分支覆盖。
- `notes[]` 只用于记录例外说明，不替代结构化字段。
