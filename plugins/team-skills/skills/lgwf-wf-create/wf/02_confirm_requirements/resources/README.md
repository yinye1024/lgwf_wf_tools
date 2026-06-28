# resources

这里存放 `confirm_requirements` 的决策结构示例与接口说明。

- `requirements_approval_example.json`：示例 `create_requirements_approval` 结构。
- 支持 `approve`、`revise`、`reject` 三类决策。
- 当前 run 只验证 proposal、approval 模板和 confirm 后固化边界说明。
- `approve` 后固化 `.lgwf/create_requirements.json`；`revise` 和 `reject` 不进入下游业务流转阶段。
