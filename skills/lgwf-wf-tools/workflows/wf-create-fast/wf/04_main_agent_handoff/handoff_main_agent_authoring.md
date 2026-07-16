# 主 agent 实现交接

当前 `wf-create-fast` 已完成需求确认、业务流确认和 scaffold 落盘。请继续当前创建任务，不要启动其他 workflow。

主 agent 必须：

- 读取 `.lgwf/main_agent_authoring_handoff.json`。
- 读取 handoff payload 中列出的 `source_artifacts`。
- 只修改 `edit_dirs` 中的目标 package。
- 基于已确认需求、业务流和已落盘 scaffold 直接完善目标 workflow package。
- 不生成 `.lgwf/step_designs.json`。
- 不调用 `wf-create` 的 `03_confirm_step_designs` 或 `04_implement_steps_react`。
- 不自动启动 `wf-post-fix` 或其他下游 workflow。
- 完成后运行 handoff payload 中的 `validation_commands`。

如果需求不足，请做保守假设并在最终说明里列出，不要回退到标准 `wf-create` 链路。
