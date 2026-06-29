# Script Flow E2E 质量规范

脚本级 E2E 的职责是覆盖目标 workflow 的脚本分支、route 分支和状态 artifact 契约。它不启动 `lgwf.py run`，不依赖真实 Codex，也不验证 runtime 编排。

必须覆盖：

- 目标 workflow 中可静态识别的 `PY SCRIPT`。
- `ROUTE WHEN` 的每个 route value。
- `APPROVAL PERSIST` 对应的审批决策输入文件。
- 关键 `.lgwf/*.json` 的写入、读取和断言。

禁止：

- 在脚本级测试中启动目标 workflow runtime。
- 使用真实 Codex。
- 把 runtime fake 或真实业务正向验收混入本测试。
