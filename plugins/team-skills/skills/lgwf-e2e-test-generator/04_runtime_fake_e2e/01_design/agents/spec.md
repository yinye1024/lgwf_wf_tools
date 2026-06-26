# Runtime Fake E2E 质量规范

runtime fake E2E 的职责是启动真实 LGWF runtime，验证目标 workflow 的编排连通、approval 驱动和关键 artifact 产出。

必须满足：

- 启动 `lgwf.py run --workflow-lgwf`。
- 使用 `status` 轮询运行状态。
- 使用 `approval get` 和 `approval submit` 自动处理人工审批。
- 使用 Python fake Codex。
- fake Codex 通过 `--prompt-file <path>` 读取 handoff prompt。
- fake 输出按 node id 或 `Main prompt file` 固定映射，不依赖调用顺序。
- 设计 `scenarios[]`，至少包含 `happy_path` 和一个非 happy path 的业务路由场景。
- 非 happy path 必须用 fake Codex 或 fake 脚本稳定触发，不能依赖调用顺序或真实时间碰运气。
- 如果目标 workflow 含有 `APPROVAL`、`ROUTE`、`REACT ON_MAX`、`AGENT_LOOP`、repair/retry 或人工门禁语义，runtime fake E2E 不得只覆盖全部节点直接 pass 的 happy path。
- 分支选择优先级：人工确认门禁 > `REACT ON_MAX` / repair retry > 非默认 `ROUTE WHEN` > `AGENT_LOOP` stop/block > 普通 approval happy path。
- 每个 scenario 必须明确：
  - `scenario_id`：用于生成 `test_<scenario_id>`。
  - `trigger`：fake Codex 输出、fake 脚本状态或 route 条件如何触发。
  - `expected_runtime_path`：预期经过的关键节点或 route。
  - `approval_decisions`：需要自动提交的 approval 值；没有则为空数组。
  - `assertions`：artifact、route、attempts、history_count、task status 或后续节点执行断言。
  - `covered_branches`：覆盖的 approval、route、repair/retry、ON_MAX 或 agent loop 分支。
- 人工确认门禁场景应模拟 `manual_approval_required -> APPROVAL -> approve -> 后续 task 继续`，并断言不会回到错误的前序 Codex repair loop。
- route/retry 场景应断言实际 route、attempts 或 history_count，而不是只断言 workflow completed。
- 无法稳定覆盖的候选分支必须写入 `coverage_gaps[]`，并说明是否阻断生成通过。

禁止：

- 使用 JS shim 或 `node_modules` 伪造 Codex。
- 将长 prompt 拼到 `.cmd` 命令行。
- 使用真实 Codex。
