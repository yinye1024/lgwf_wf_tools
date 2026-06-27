# LGWF Runtime 辅助

用于运行层操作：执行已有 `workflow.json`、验证 CLI、调试 client runner 结果。它不负责功能开发、workflow 创建或 prompt 设计。

## 执行 Workflow

执行前必须明确：

- `workflow_json`：可执行 `workflow.json` 路径。
- `work_dir`：runner 执行和 `.lgwf/runs/` 写入的 workspace 目录。
- `input_json`：JSON object 字符串，默认 `{}`。

Agent 通过统一 facade `scripts/lgwf.py` 运行：

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-json <workflow_json> --work-dir <work_dir> --input-json "{}"
```

旧 client CLI 只用于兼容排障，见 `references/compatibility-cli.md`。

如果 `.venv` 不可用，只能在确认项目已安装或 `PYTHONPATH=src` 已设置后使用当前 Python。

## 运行规则

- 不从 Markdown 推断 `workflow.json`；使用显式路径。
- `workflow.json` 是 runtime IR 和执行入口。
- stdout 是机器可读 final-state JSON。
- stderr 是进度和错误文本。
- 使用 `--record true` 时，run records 写入 `<work_dir>\.lgwf\runs\`。
- 包含 `AGENT_LOOP` / `subgraph.agent_loop` 的 workflow 还会在 `<work_dir>\.lgwf\loops\<loop_id>\` 写入 `loop.json`、`iterations.json`、`report.json`、`current/*.json` 和每轮 `iterations/NNN/` 归档；排障时优先读取这些 artifacts。
- runtime metrics 会在 final state 中写入 `state.run.token_usage` 和 `state.run.node_timings`；节点级 Codex token 事实位于 `state.token_usage.<node_id>`。`AGENT_LOOP TOKEN_MAX` 根据 run token usage 的本轮增量判断。

## 调试顺序

- 先确认 CLI 参数、`workflow_json` 文件、`work_dir` 和 `input_json`。
- 再查看 stderr 中的 workflow/node 进度。
- 如果 `AGENT_LOOP` 停在 `waiting_human`，检查 `state.agent_loop.<id>.status` 或显式 `STATUS` path，而不一定会存在 `.lgwf/human/*.request.json`；这是 loop 控制状态，不等同于 `flow.human_approval` pending request。
- runner 结果异常时，读取相关 `lgwf_client.runners.*` 源码和测试。

## 边界

- 创建或修改 workflow 目录：读取 `references/dsl-assist/guide.md`。
- 创建、审核或优化 prompt：读取 `references/prompt-assist/guide.md`。
- 修改 runtime/client 代码功能不属于分发版 `lgwf-client-assist` 的职责。

## 验证

修改 CLI、runtime/client 执行链路或 runner 后运行：

```powershell
.venv\Scripts\python.exe -m unittest discover -s test -p "test_lgwf_client_cli.py"
.venv\Scripts\python.exe -m compileall -q src test
```
