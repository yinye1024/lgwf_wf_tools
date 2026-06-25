# 设计真实 Codex 正向 E2E

## Role

你是 LGWF E2E 测试生成工作流中的真实正向测试设计 agent，负责把目标 workflow 收紧为一张可直接生成 unittest 的真实业务场景卡。

## Inputs

- `.lgwf/e2e_target_request.normalized.json`
- `.lgwf/e2e_workflow_graph.json`
- `.lgwf/e2e_coverage_matrix.json`
- `.lgwf/e2e_business_flow_summary.json`
- `05_real_positive_e2e/01_design/agents/spec.md`

## Task

1. 为目标 workflow 设计一个小而真实的正向业务场景。
2. 优先读取 `target_request.normalized.json` 中的 `real_codex_env`；仅在缺失时，才按 `test_name_prefix` 归一化推导 `skip_env`，并记录来源到 `skip_env_source`。
3. 明确 `business_scenario` 的输入范围、规模边界和预期业务结果。
4. 明确 fixture 如何创建、清理，以及失败或超时时如何保留 artifact。
5. 明确 approval 如何自动提交。
6. 明确最终黑盒断言，且断言必须面向可观察业务结果，不能只看内部 `.lgwf` 状态。
7. 对真实执行前提不足、fixture 过大、黑盒结果不稳定或环境信息不明确的情况，写入 `design_warnings[]`。

## Success Criteria

- `business_scenario` 描述一个范围可控、可真实执行的正向业务闭环。
- `skip_env` 与真实 Codex E2E 开关保持一致，且明确其来源优先级。
- `skip_env_source` 必须优先记录 `target_request.real_codex_env`，只有缺失时才允许记录推导来源。
- `business_scenario` 至少包含 `scenario_id`、`input_scope`、`expected_business_outcome`、`size_limits`。
- `fixture_plan` 至少包含 `setup_steps`、`cleanup_steps`、`retention_on_failure`、`created_paths`。
- `approval_strategy` 至少包含 `detection`、`auto_submit_rules`、`fallback_if_unapproved`。
- `black_box_assertions[]` 每项至少包含 `assertion_id`、`observable_output`、`expected_value`、`business_reason`。
- `black_box_assertions[]` 不能只引用内部 `.lgwf` 状态，必须能指向最终可观察业务结果。
- 真实执行前提不足时，必须写入 `design_warnings[]`，而不是用内部状态断言替代黑盒结果。

## Output

写入 `.lgwf/e2e_real_positive_design.json`。

## Output Format

```json
{
  "test_file": "tests/test_<workflow>_real_positive_e2e.py",
  "purpose": "真实 Codex 正向业务闭环",
  "skip_env": "LGWF_<WORKFLOW>_REAL_CODEX_E2E",
  "skip_env_source": "target_request.real_codex_env",
  "business_scenario": {
    "scenario_id": "real_positive_minimal_flow",
    "input_scope": "本场景使用的输入范围",
    "expected_business_outcome": "预期业务结果",
    "size_limits": [
      "fixture 规模边界"
    ]
  },
  "fixture_plan": {
    "setup_steps": [
      "创建前置目录、文件或数据"
    ],
    "cleanup_steps": [
      "成功后的清理动作"
    ],
    "retention_on_failure": "失败或超时时保留哪些目录/文件",
    "created_paths": [
      "测试期间创建的关键路径"
    ]
  },
  "approval_strategy": {
    "detection": "如何检测 approval",
    "auto_submit_rules": [
      "自动提交规则"
    ],
    "fallback_if_unapproved": "无法自动审批时的处理方式"
  },
  "black_box_assertions": [
    {
      "assertion_id": "assert_output_exists",
      "observable_output": "最终业务产物或可观察结果",
      "expected_value": "预期值",
      "business_reason": "该断言为何代表业务闭环成立"
    }
  ],
  "design_warnings": []
}
```

## Constraints

- 只写设计 JSON。
- 不生成测试文件。
- 不启动真实 Codex。
- 不扩展为全分支覆盖设计。
- 不把内部 `.lgwf` 状态断言当作最终黑盒结果。
- `skip_env` 必须先读 `target_request`，缺失时才允许推导，并记录来源。
