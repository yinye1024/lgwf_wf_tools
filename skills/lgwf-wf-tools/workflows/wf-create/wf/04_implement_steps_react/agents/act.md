# implement_steps_react act

## Role
你是步骤实现 ACT 子流程的总说明。本阶段已拆为 `ACT WORKFLOW implement_units`：先由脚本准备 implementation units，再通过 `FOREACH` 调用单 unit Codex，最后由脚本合并为 `.lgwf/implementation_result.json`。

## Inputs
- `agents/spec.md`：本 ReAct 循环的共同准则，是路径、拓扑、DSL 和排除范围的权威约束。
- `.lgwf/implementation_reason.md`：本轮 reason 产出的实现或修复计划。
- `.lgwf/step_designs.json`：已确认的步骤设计固化结果。
- `.lgwf/implementation_context.json`：确定性路径上下文。
- `docs/steps/*.md`：已批准的步骤设计文档。
- `state.lgwf_wf_create.implementation_units`：由 `prepare_implementation_units.py` 生成的最小实现或修复单元。
- `state.lgwf_wf_create.implementation_unit_results.items`：`FOREACH implement_each_unit` 收集的单 unit 实现结果列表；`merge_implementation_results.py` 读取父对象 `state.lgwf_wf_create.implementation_unit_results`。
- `state.lgwf_wf_create.scaffold_package_result.scaffold_plan`：确定性脚手架计划，包含 `package_profile`、模板元信息、目录和文件计划。
- scaffold context file `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md`：由 workflow resource `02_confirm_business_flow/resources/scaffold_template_spec.md` 镜像而来。
- scaffold context file `.lgwf/create_reference_context/scaffold/scaffold_package_template.json`：由 workflow resource `02_confirm_business_flow/resources/scaffold_package_template.json` 镜像而来，作为生成文件清单和 profile 语义的参考。
- `.lgwf/create_reference_context/dsl-assist/create-workflow.md`、`.lgwf/create_reference_context/dsl-assist/guide.md` 和 `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md`：facade 内置 bundled client 的 DSL 创建、审计和 workflow 拆分规范。
- `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`：workflow 模块化创建总纲。
- `.lgwf/implementation_observe.json`：如果存在，必须优先修复其中确定性 audit 失败项。
- 当前 target package 中已存在、且被批准步骤明确引用的相关文件与目录。

## Task
1. `prepare_implementation_units.py` 读取 `agents/spec.md` 之外的运行上下文，将已确认步骤设计拆成互不重叠的 implementation units。
2. `FOREACH implement_each_unit` 对每个 unit 启动 `implement_one_unit.lgwf`，由 `agents/act_unit.md` 约束单个 Codex 的实际写入范围。
3. 如果 `.lgwf/implementation_observe.json` 存在且 audit 失败，本轮只生成与失败项相关的 units；无法归因时才回退到根编排和阶段 unit。
4. `merge_implementation_results.py` 合并每个 unit 的结果，记录本轮实际生成的文件、目录、步骤设计文档副本、占位内容、剩余风险和本轮处理的 audit 反馈。

## Resume And Budget Rules
- 如果目标目录里已存在的目标 package 只有部分文件，把它视为本轮可续写草稿；先读取精简文件清单，先补齐缺失的必需文件，除非 audit 反馈要求，不重写已经成型的文件。
- resume 后优先完成 `wf/docs/steps/`、各阶段 `workflow.lgwf`、阶段私有 `agents/`、`scripts/`、`resources/`、根契约和最小测试这些必需项，再考虑说明性优化。
- 避免重新展开大范围参考阅读；已读过的设计文档、DSL 参考和仓库范式只在需要修正具体文件时按路径回看。
- 在执行昂贵校验或可选完善前，先确保每个 unit 都能写出 `.lgwf/current_implementation_unit_result.json`，并由 merge 阶段生成 `.lgwf/implementation_result.json`，避免超时后没有结构化交接。

## Success Criteria
- 生成结果满足 `agents/spec.md` 的共同准则。
- 生成的初稿文件可继续验收。
- 输出结果清楚记录生成范围、占位内容、剩余风险和已处理的 observe 反馈。

## Output
由 `merge_implementation_results.py` 写入 `.lgwf/implementation_result.json`，说明本阶段生成或计划生成的 workflow 初稿文件、目录和剩余风险。

## Output Format
输出 UTF-8 JSON，至少说明：
- `status`：`ok` 或 `failed`。
- `target_package_root`。
- 本轮生成或修改了哪些 workflow 初稿文件与目录。
- 每个文件或目录对应哪个已批准步骤。
- 哪些内容仍是占位，原因是什么，后续如何补齐。
- 本轮处理了哪些 audit 反馈。

## Constraints
- 本节点不得覆盖 `agents/spec.md` 的共同准则。
- 除 reason 计划和 observe 反馈指定的实现范围外，不做额外整理。
