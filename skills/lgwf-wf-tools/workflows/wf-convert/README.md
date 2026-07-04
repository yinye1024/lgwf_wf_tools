# lgwf-wf-convert

`lgwf-wf-convert` 用于把现有 prompt workflow 目录转换为 `wf-create` 可消费的输入包。它是 `lgwf-wf-tools` 的内部 workflow package。

## 当前范围

- 收集待转换 prompt workflow 的目标目录和输出目标。
- 索引 prompt、agent、resource、README、workflow 说明等文本文件。
- 使用 ReAct 分析源 prompt workflow 的结构、职责、业务契约和缺口。
- 区分必须迁移的业务逻辑与不迁移的 prompt 执行技巧，例如执行矩阵、预填充、few-shot、角色强化和格式诱导。
- 使用 ReAct 生成 `wf-create` 创建输入 proposal、`conversion_mapping` 和 `parity_requirements`。
- 人工确认 proposal 后固化为 `.lgwf/wf_create_payload.json`。
- 通过映射节点提取 `wf-create` 输入，再用原生 `RUN_WORKFLOW` 节点启动后续 `wf-create`。
- 在 `wf-create` 完成后生成 `.lgwf/business_parity_report.json`，并把一致性审查结果写入转换报告和 `wf-post-fix` handoff。

## 不做的事

- 不直接生成最终目标 LGWF workflow。
- 不跳过 `wf-create` 自身的人工确认；`wf-convert` 只负责把已确认的转换输入传给 `wf-create`。
- 不自动调用 `wf-prompt-fix`、`wf-prompt-upgrade` 或 `wf-fix`。
- 不保证源 workflow 业务 happy path 成功。
- 业务一致性审查只检查契约覆盖，不替代真实 E2E 运行验证。

## 运行状态

运行状态只写入 `ws/.lgwf`。目标 package 根目录不得写入 `.lgwf`。
