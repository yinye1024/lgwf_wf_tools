# resources

这里存放 `confirm_business_flow` 的决策结构示例与接口说明。

- `business_flow_approval_example.json`：示例 `business_flow_approval` 结构。
- 支持 `approve`、`revise`、`reject` 三类决策。
- 字段命名需要与 `confirm_business_flow` 节点和 `business_flow_proposal` 中的阶段/节点命名保持一致。
- 当前 run 只验证 proposal、approval 模板和 confirm 后固化边界说明。
- `approve` 后固化 `.lgwf/business_flow.json`；`revise` 和 `reject` 不进入下游 scaffold 落盘和主 agent handoff 阶段。
