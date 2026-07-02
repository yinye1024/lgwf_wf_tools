# lgwf-wf-convert

`lgwf-wf-convert` 用于把现有 prompt workflow 目录转换为 `wf-create` 可消费的输入包。它是 `lgwf-wf-tools` 的内部 workflow package。

## 第一版范围

- 收集待转换 prompt workflow 的目标目录和输出目标。
- 索引 prompt、agent、resource、README、workflow 说明等文本文件。
- 使用 ReAct 分析源 prompt workflow 的结构、职责和缺口。
- 使用 ReAct 生成 `wf-create` 创建输入 proposal。
- 人工确认 proposal 后固化为 `.lgwf/wf_create_payload.json`。
- 输出转换报告。
- 通过原生 `RUN_WORKFLOW` 节点把 `wf_create_payload.wf_create_payload` 作为输入启动后续 `wf-create`。

## 不做的事

- 不直接生成最终目标 LGWF workflow。
- 不跳过 `wf-create` 自身的人工确认；`wf-convert` 只负责把已确认的转换输入传给 `wf-create`。
- 不自动调用 `wf-prompt-fix`、`wf-prompt-upgrade` 或 `wf-fix`。
- 不保证源 workflow 业务 happy path 成功。

## 运行状态

运行状态只写入 `ws/.lgwf`。目标 package 根目录不得写入 `.lgwf`。
