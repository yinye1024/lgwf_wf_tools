# 静态审批路由 prompt workflow

该样例用于真实端到端测试：把一个固定的 prompt workflow 转换为 LGWF workflow 初稿。

编排入口：`flow/workflow.md`。

业务目标：

- 收集一条审批请求。
- 根据金额和风险等级决定是否需要人工复核。
- 输出审批结果、路由原因和审计摘要。

核心规则：

- 金额小于 1000 且风险等级为 low 时自动通过。
- 金额大于等于 1000 或风险等级为 high 时进入人工复核。
- 所有路径都必须记录 audit trail。
