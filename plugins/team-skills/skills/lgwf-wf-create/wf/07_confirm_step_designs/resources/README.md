# resources

这里存放 `confirm_step_designs` 的决策结构示例与接口说明。

- `step_design_approval_example.json`：示例 `step_design_confirmation_record` 结构。
- 支持 `approve`、`revise`、`reject` 三类决策。
- `approved_step_slugs` 用于追踪哪些设计文档已经可以进入 `implement_steps_react`。
- 当前 run 只验证设计文档草案、approval 模板和确认后固化边界说明。
- `approve` 后固化 `.lgwf/step_designs.json`；`revise` 和 `reject` 不进入实现阶段。
