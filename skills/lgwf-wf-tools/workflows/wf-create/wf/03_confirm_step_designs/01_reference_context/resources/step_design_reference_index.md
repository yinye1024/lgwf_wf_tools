# create_reference_context 索引

本索引用于 `step_design_proposal` 的首轮设计和后续修复 Codex 节点按需读取参考资料。默认先阅读本文件，不要一次性读取整个 `create_reference_context` 目录。

## 读取顺序

1. 先阅读当前节点 prompt、已确认需求、已确认业务流和 scaffold plan。
2. 再阅读本索引，判断当前任务需要哪些参考资料。
3. 只读取与当前判断直接相关的参考文件；不要把参考目录当作分析目标目录。

## 参考资料路由

- 需要设计 `workflow.lgwf`、节点、`FLOW`、`CONTRACT` 或 resource path 时，阅读 `dsl-assist/create-workflow.md`。
- 需要确认 DSL 静态审计、读写消费链、节点 contract 或 workflow audit 要求时，阅读 `dsl-assist/workflow-audit-checklist.md`。
- 需要理解 bundled client 的整体 DSL 使用指引时，阅读 `dsl-assist/guide.md`。
- 需要理解 `scaffold_plan`、`package_profile`、目录结构、文件清单、placeholder 或阶段 manifest 时，以 `.lgwf/scaffold_package_result.json` 为准。
- 需要划分 workflow、子 workflow、复杂 step、状态边界和恢复边界时，阅读 `workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`。
- 需要补齐模块入口文档、依赖、状态边界、产物、验证和禁止事项时，阅读 `module-contract/module-contract.md`。

## 使用约束

- 参考资料只提供规则和约束，不是目标 workflow 的业务输入。
- 步骤设计阶段不得重新读取入口参考资料、目标 package 目录、测试目录或实现阶段目录。
- 如果 index 与当前节点 prompt 冲突，以当前节点 prompt 和 LGWF node contract 为准。
