# 主 agent 实现交接

当前 `wf-create-fast` 已完成需求确认、业务流确认和 scaffold 落盘。请继续当前创建任务，不要启动其他 workflow。

主 agent 必须：

- 读取 `.lgwf/main_agent_authoring_handoff.json`。
- 读取 handoff 中 `confirmed_requirements` 指向的 `.lgwf/create_requirements.json`。
- 读取 handoff 中 `confirmed_business_flow` 指向的 `.lgwf/business_flow.json`。
- 使用 handoff 中的 `target_package` 定位目标 package、入口 workflow、work dir、tests 目录和验证命令。
- 使用 `target_package.materialization` 核对 scaffold 实际创建和跳过的文件，并在最终说明中汇报外部目标 package 写入摘要。
- 在首次修改目标 package 前，先只读检查 confirmed artifacts 和已落盘 scaffold，再使用主 agent 的计划能力生成可见执行计划。
- 执行计划至少包含“检查上下文与 scaffold”“实现目标 package”“运行验证命令”三个阶段，并且任一时刻最多只有一个阶段处于进行中。
- 按计划逐项实施并持续更新计划状态；如果实际情况要求改变实施路径，先更新计划，再继续执行。
- 只修改 `target_package.edit_dirs` 中的目标 package。
- 基于已确认需求、业务流和目标 package 按计划完善目标 workflow package。
- 不生成 `.lgwf/step_designs.json`。
- 不调用 `wf-create` 的 `03_confirm_step_designs` 或 `04_implement_steps_react`。
- 不自动启动 `wf-post-fix` 或其他下游 workflow。
- 完成后运行 `target_package.validation_commands`。

不得跳过计划直接编辑目标 package。如果需求不足，请把保守假设写入执行计划并在最终说明里列出，不要回退到标准 `wf-create` 链路。
