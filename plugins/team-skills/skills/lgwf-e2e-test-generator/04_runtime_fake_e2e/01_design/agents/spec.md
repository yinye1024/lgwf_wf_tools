# Runtime Fake E2E 质量规范

runtime fake E2E 的职责是启动真实 LGWF runtime，验证目标 workflow 的编排连通、approval 驱动和关键 artifact 产出。

必须满足：

- 启动 `lgwf.py run --workflow-lgwf`。
- 使用 `status` 轮询运行状态。
- 使用 `approval get` 和 `approval submit` 自动处理人工审批。
- 使用 Python fake Codex。
- fake Codex 通过 `--prompt-file <path>` 读取 handoff prompt。
- fake 输出按 node id 或 `Main prompt file` 固定映射，不依赖调用顺序。

禁止：

- 使用 JS shim 或 `node_modules` 伪造 Codex。
- 将长 prompt 拼到 `.cmd` 命令行。
- 使用真实 Codex。
