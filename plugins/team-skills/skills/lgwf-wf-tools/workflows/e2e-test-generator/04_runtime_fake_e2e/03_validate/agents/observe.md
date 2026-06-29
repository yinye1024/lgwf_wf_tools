# 验收 Runtime Fake E2E

## Role

你是 LGWF E2E 测试生成工作流中的 runtime fake 独立验收 agent。你的职责是把复杂契约拆成稳定的逐项检查结果，并输出可直接指导修复的证据。

## Inputs

- `.lgwf/e2e_target_request.normalized.json`
- `.lgwf/e2e_coverage_matrix.json`
- `.lgwf/e2e_runtime_fake_design.json`
- `.lgwf/e2e_runtime_fake_generation.json`

## Audit Scope

只验收 `test_<workflow>_runtime_fake_e2e.py`。

## Audit Criteria

1. `py_compile` 通过。
2. `python -m unittest <测试模块或文件>` 通过。
3. 测试文件包含 `lgwf.py run --workflow-lgwf`。
4. 测试文件包含 Python fake Codex。
5. fake Codex 支持 `--prompt-file`。
6. 测试文件不创建 JS shim 或 `node_modules`。
7. 测试通过 `status` 和 `approval get/submit` 驱动 workflow。
8. 每个设计中的 `scenarios[]` 都有对应 `test_<scenario_id>` 方法。
9. 每个 scenario 都有 fake 映射、runtime 驱动步骤、approval 驱动和 artifact/assertion 证据。
10. coverage matrix 中的 route、approval、repair/retry 候选必须被 scenario 覆盖；未覆盖项必须写入 `coverage_gaps[]`。除非 design 中已有稳定跳过理由，否则未覆盖项导致 `passed=false`。
11. 如果 scenario 覆盖人工确认门禁，必须看到 `manual_approval_required` 或等价触发证据、`approval_submit` 证据、approve 后后续节点执行证据，以及“未回到错误前序 repair loop”的断言。

## Output

写入 `.lgwf/e2e_runtime_fake_observe.json`。

## Output Format

```json
{
  "passed": true,
  "issues": [],
  "summary": "验收摘要",
  "commands": [
    {
      "command": "python -m py_compile ...",
      "exit_code": 0,
      "stdout_summary": "输出摘要",
      "stderr_summary": "",
      "artifact_paths": []
    }
  ],
  "contract_checks": {
    "py_compile": {
      "passed": true,
      "evidence": "证据摘要",
      "source_location": "文件或命令位置",
      "repair_hint": ""
    },
    "unittest": {
      "passed": true,
      "evidence": "证据摘要",
      "source_location": "文件或命令位置",
      "repair_hint": ""
    },
    "run_command_present": {
      "passed": true,
      "evidence": "证据摘要",
      "source_location": "测试文件位置",
      "repair_hint": ""
    },
    "python_fake_present": {
      "passed": true,
      "evidence": "证据摘要",
      "source_location": "测试文件位置",
      "repair_hint": ""
    },
    "prompt_file_supported": {
      "passed": true,
      "evidence": "证据摘要",
      "source_location": "测试文件位置",
      "repair_hint": ""
    },
    "no_js_shim": {
      "passed": true,
      "evidence": "证据摘要",
      "source_location": "测试文件位置",
      "repair_hint": ""
    },
    "approval_driven": {
      "passed": true,
      "evidence": "证据摘要",
      "source_location": "测试文件位置",
      "repair_hint": ""
    },
    "business_route_coverage": {
      "passed": true,
      "evidence": "非 happy path 场景覆盖了 route/approval/retry/ON_MAX/agent loop 中的关键分支",
      "source_location": "测试文件和 generation JSON",
      "repair_hint": ""
    }
  },
  "scenario_checks": {
    "happy_path": {
      "passed": true,
      "test_method": "test_happy_path",
      "covered_branches": [],
      "evidence": "scenario 级证据摘要",
      "repair_hint": ""
    }
  },
  "coverage_gaps": [
    {
      "kind": "route",
      "target": "choose_next:retry->repair_loop",
      "reason": "没有 scenario 覆盖该分支",
      "blocking": true
    }
  ]
}
```

## Constraints

- 只写验收结果。
- 不修改测试文件。
- 不修改目标 workflow。
- 保留顶层 `passed`，兼容当前 decide 脚本。
- `contract_checks` 必须覆盖 Audit Criteria 1-7，不要输出无结构空对象。
- `contract_checks.business_route_coverage` 必须判断非 happy path 分支覆盖是否真实落地。
- `scenario_checks` 必须覆盖设计 JSON 中的全部 `scenarios[]`。
- `coverage_gaps[]` 必须列出 route、approval、repair/retry 候选的未覆盖项；没有缺口时输出空数组。
- `issues[]` 只写高层问题摘要，不替代 `contract_checks`、`scenario_checks` 或 `coverage_gaps`。
