# lgwf-wf-convert

`lgwf-wf-convert` 用于把现有 prompt workflow 目录转换为 `wf-create` 可消费的输入包。它是 `lgwf-wf-tools` 的内部 workflow package。

## 当前范围

- 收集待转换 prompt workflow 的目标目录和输出目标。
- 索引 prompt、agent、resource、README、workflow 说明等文本文件。
- 使用 ReAct 分析源 prompt workflow 的结构、职责、业务契约和缺口。
- 区分必须迁移的业务逻辑与不迁移的 prompt 执行技巧，例如执行矩阵、预填充、few-shot、角色强化和格式诱导。
- 使用 ReAct 生成 `wf-create` 创建输入 proposal、`conversion_mapping` 和 `parity_requirements`。
- 人工确认 proposal 后固化为 `.lgwf/wf_create_payload.json`。
- 通过映射节点提取 `wf-create` 输入，把 `source_root` 作为新版 `request.target_dir` 只读资料目录传给下游，再用原生 `RUN_WORKFLOW` 节点启动后续 `wf-create`。
- 在 `wf-create` 完成后生成 `.lgwf/business_parity_report.json`，并把一致性审查结果写入转换报告和 `wf-post-fix` handoff。

## 不做的事

- 不直接生成最终目标 LGWF workflow。
- 不跳过 `wf-create` 自身的人工确认；`wf-convert` 只负责把已确认的转换输入传给 `wf-create`。
- 不自动调用 `wf-prompt-fix`、`wf-prompt-upgrade` 或 `wf-fix`。
- 不保证源 workflow 业务 happy path 成功。
- 业务一致性审查只检查契约覆盖，不替代真实 E2E 运行验证。

## 运行状态

运行状态只写入 `ws/.lgwf`。目标 package 根目录不得写入 `.lgwf`。

## `wf-create` 输入兼容

`wf-convert` 固化的 `wf-create` 输入必须保留顶层 `raw_intent`，并可附带 `source_business_contract`、`conversion_mapping` 和 `prompt_workflow_context`。源 prompt workflow 目录通过 `request.target_dir` 传给 `wf-create`，只作为创建阶段的只读上下文，不表示目标输出目录。

`map_wf_create_input.py` 需要同时兼容旧的 `{ "wf_create_payload": ... }` 包装和已经扁平化的 `wf-create` 输入；无论哪种形状，进入 `RUN_WORKFLOW wf_create` 前都必须有非空 `raw_intent`。

## ReAct 反馈闭环

`propose_create_input_react` 的 `observe` 必须输出结构化 `issues`。每个 issue 包含 `blocking`：

- `blocking=true`：会阻塞人工确认、confirmed 原样复用或 payload 固化，`decide_create_input.py` 会继续下一轮 ReAct。
- `blocking=false`：只影响人工关注或后续运行质量，`decide_create_input.py` 会退出到 `confirm_create_input`，由人工确认处理。

下一轮 `reason` 同时读取 `.lgwf/wf_create_input_observe.json` 和 `.lgwf/wf_create_input_proposal.json`，必须生成 `issue_resolution_plan`。`act` 按该计划最小修复上一轮 proposal，避免无关重写。第一轮由 `index_prompt_files.py` 创建空的 `.lgwf/wf_create_input_proposal.json` 占位文件，确保 context 文件存在。
