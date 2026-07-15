# TOOL 节点

稳定的 client 工具优先使用原生 `TOOL`；workflow 专属 Python 逻辑继续使用 `PY`。

```lgwf
TOOL copy_assets
  USE copy_directory
  OPTIONS {
    "source": "assets",
    "destination": "output/assets",
    "overwrite": true
  }
  TIMEOUT 300
  RESULT state.copy_result;
```

- `USE` 必填，并且只能引用 `scripts/lgwf.py tool list` 中的公开 tool。
- `OPTIONS` 可选，必须是标准 JSON object，key 使用双引号；默认 `{}`。
- `TIMEOUT` 可选，沿用 workflow defaults。
- `RESULT` 可选，默认写入 `results.{node}`。
- 不支持 `INSTRUCTION` 或 `OPTIONS_FROM`。
- `TOOL` 可用于顶层、`REACT` slot、`AGENT_LOOP` slot 和 `PARALLEL STEP`。
- workflow 中的所有 tool 路径都限制在 `work_dir`，禁止绝对路径、`..` 和链接逃逸。

初始公开 tool：

- `ensure_dir`
- `write_text_file`
- `file_replace`
- `copy_file`
- `copy_directory`
- `lgwf_dsl_cli`

`lgwf_dsl_cli` 用于在 workflow runtime 内执行受限的 `lgwf_dsl.cli` authoring 命令：

- `compile`：把 `.lgwf` 编译为 workflow JSON，要求 `compile_output_path`。
- `explain`：输出 workflow 结构摘要。
- `lint`：检查 authoring 风险模式。
- `audit`：输出机器可读 diagnostics，适合作为 observe gate。
- `schema`：输出 DSL schema。

示例：

```lgwf
TOOL audit_generated_workflow
  USE lgwf_dsl_cli
  OPTIONS {
    "command": "audit",
    "input": "skills/example/wf/workflow.lgwf",
    "result_output_path": ".lgwf/example_audit_result.json",
    "include_stdout": true,
    "fail_on_command_failure": false
  }
  RESULT state.example.audit_result
  CONTRACT {
    WRITE workspace file ".lgwf/example_audit_result.json";
  };
```

`lgwf_dsl_cli` 不暴露 `lgwf.py` 控制面能力；`run`、`status`、`stop`、`approval`、`review` 和 `runs` 仍由 facade 或主 agent 调用。权威字段 schema 以 `scripts/lgwf.py tool schema lgwf_dsl_cli` 返回结果为准；完整 descriptor 可用 `scripts/lgwf.py tool describe lgwf_dsl_cli` 查看。

新增 tool 时扩展机器可读 tool catalog、共享 operation 和测试，不修改 `TOOL` parser、lowering 或 `exec.run_tool`。
