# implementation_reference_context 索引

本索引用于 `implement_steps_react` 实现阶段按需读取 DSL、audit 和 workflow 模块化参考资料。实现阶段的设计范围只能来自 `.lgwf/step_designs.json`；本目录下的参考资料只说明“如何写出合法的 LGWF workflow package”，不得用于扩展、改写或补充已确认步骤设计。

## 读取顺序

1. 先读取 `.lgwf/step_designs.json`、`.lgwf/scaffold_package_result.json` 和 `.lgwf/implementation_context.json`，确认本轮实现范围、目录事实和目标路径。
2. 再读取本索引，判断需要哪些技术参考资料。
3. 只按当前文件类型和 audit 失败项读取 `.lgwf/create_reference_context` 下的具体资料；不要为了实现阶段一次性展开全部参考内容。

## 参考路由

- 需要创建或修复 `workflow.lgwf`、`FLOW`、`STEP`、`REACT`、`CONTRACT`、`RESOURCE` 路径或节点字段时，阅读 `dsl-assist/create-workflow.md` 和 `dsl-assist/guide.md`。
- 需要解释 `lgwf.py audit` 失败、修复 DSL authoring 问题或确认 workflow 结构性验收项时，阅读 `dsl-assist/workflow-audit-checklist.md`。
- 需要确认根 workflow、阶段 workflow、目录边界、运行状态隔离、子 workflow 自包含和验证入口时，阅读 `workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`。
- 需要补齐目标 package 的入口文档、模块定位、依赖、状态边界、产物、验证和禁止事项时，阅读 `module-contract/module-contract.md`。

## 边界

- `.lgwf/step_designs.json` 是唯一设计契约；参考资料不得覆盖其中的 `goal`、`inputs`、`outputs`、`dependencies`、`implementation_suggestions`、`acceptance_notes` 和 `out_of_scope`。
- `.lgwf/scaffold_package_result.json` 和 `.lgwf/implementation_context.json` 是确定性辅助事实；参考资料不得推翻其中的目录、文件计划或路径边界。
- 如果参考资料与已确认步骤设计冲突，应在实现结果或 observe 中记录阻塞原因，不得静默改设计。
