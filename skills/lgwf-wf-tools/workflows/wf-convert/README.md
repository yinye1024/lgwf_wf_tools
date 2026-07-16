# lgwf-wf-convert

`lgwf-wf-convert` 用于把现有 prompt workflow 目录转换为 `wf-create-fast` 可消费的完整 target file。它是 `lgwf-wf-tools` 的内部 workflow package。

## 当前范围

- 收集待转换 prompt workflow 的目标目录和输出目标。
- 索引 prompt、agent、resource、README、workflow 说明等文本文件。
- 使用 ReAct 分析源 prompt workflow 的结构、职责、业务契约和缺口。
- 区分必须迁移的业务逻辑与不迁移的 prompt 执行技巧，例如执行矩阵、预填充、few-shot、角色强化和格式诱导。
- 使用 ReAct 生成 `wf-create-fast` 创建输入 proposal、`conversion_mapping` 和 `parity_requirements`。
- 人工确认 proposal 后固化为 `.lgwf/wf_create_fast_input.json`。
- 写入 `.lgwf/wf_create_fast_handoff.json` 作为完整 handoff target file。
- HANDOFF 给主 agent，由主 agent 把该 handoff target file 作为 `wf-create-fast` 的 `request.target_file` 启动后续创建流程。

## 不做的事

- 不在 `wf-convert` 内直接完成最终目标 LGWF workflow 实现；最终实现由 `wf-create-fast` 的 handoff 交给主 agent。
- 不在 `wf-convert` 内直接启动 `wf-create-fast`，也不生成转换报告或业务一致性报告；`wf-convert` 只负责把已确认的转换输入 handoff 给主 agent。
- 不跳过 `wf-create-fast` 的需求、业务流、scaffold 和 handoff 边界。
- 不自动调用标准创建实现链路、`wf-prompt-fix`、`wf-prompt-upgrade`、`wf-fix` 或 `wf-post-fix`。
- 不保证源 workflow 业务 happy path 成功。

## 运行状态

运行状态只写入 `ws/.lgwf`。目标 package 根目录不得写入 `.lgwf`。

## `wf-create-fast` handoff

`.lgwf/wf_create_fast_handoff.json` 是 `wf-convert` 交给 `wf-create-fast` 的完整 target file，包含 `raw_intent`、`workflow_name`、`target_package_root`、`source_business_contract`、`conversion_mapping` 和 `prompt_workflow_context`。

主 agent 接手后创建一个小的 `wf-create-fast` 启动输入，其中 `request.target_file` 指向 `.lgwf/wf_create_fast_handoff.json`。

## ReAct 反馈闭环

`propose_create_input_react` 的 `observe` 必须输出结构化 `issues`。每个 issue 包含 `blocking`：

- `blocking=true`：会阻塞人工确认、confirmed 原样复用或 handoff target 固化，`decide_create_input.py` 会继续下一轮 ReAct。
- `blocking=false`：只影响人工关注或后续运行质量，`decide_create_input.py` 会退出到 `confirm_create_input`，由人工确认处理。

下一轮 `reason` 同时读取 `.lgwf/wf_create_fast_input_observe.json` 和 `.lgwf/wf_create_fast_input_proposal.json`，必须生成 `issue_resolution_plan`。`act` 按该计划最小修复上一轮 proposal，避免无关重写。第一轮由 `index_prompt_files.py` 创建空的 `.lgwf/wf_create_fast_input_proposal.json` 占位文件，确保 context 文件存在。
