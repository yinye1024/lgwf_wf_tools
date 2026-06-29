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

新增 tool 时扩展机器可读 tool catalog、共享 operation 和测试，不修改 `TOOL` parser、lowering 或 `exec.run_tool`。
