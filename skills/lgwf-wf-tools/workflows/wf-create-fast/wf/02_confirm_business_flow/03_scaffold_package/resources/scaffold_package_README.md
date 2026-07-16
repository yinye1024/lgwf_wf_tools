# scaffold_package 资源说明

这里存放 `scaffold_package` 阶段的规则说明、模板资源与结果契约文档。

- `scaffold_template_spec.md`：给 ReAct 节点和人工审阅者读取的 package 模板规范。
- `scaffold_package_template.json`：给 `scaffold_package.py` 读取的机器模板。
- `scaffold_result_contract.md`：定义 `scaffold_package` 输出的 `scaffold_plan` 契约。

- `scaffold_result_contract.md`：定义 `scaffold_result` 的结构、创建清单和边界约束。

当前阶段只交付确定性脚手架规则与验证说明：

- 输入基于已确认需求和 `business_flow_proposal` 可推导出的阶段信息。
- 输出是“后续将由实现阶段发布什么”的 `scaffold_result` 计划，采用外层目录加 `wf/` 唯一 workflow package root 的布局。
- 当前 run 只有在 `confirm_business_flow` 为 `approve` 时才固化 `.lgwf/business_flow.json`。
- 脚手架只生成目标 package 框架计划，不创建或覆盖目标 package 真实文件，不向目标 package 根目录写入 `.lgwf`。
- 运行状态边界仍归 `ws/.lgwf`。
