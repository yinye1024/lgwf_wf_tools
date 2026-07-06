# prepare-target-manifest

## step_slug
`prepare-target-manifest`

## step_name
目标清单与包结构护栏设计

## goal
设计 `collect_targets` 第一层子 workflow，先把 `wf-dsl-upgrade` 目标 package 的整体结构、根 `wf/workflow.lgwf` 薄编排边界和目标清单生成逻辑固定下来，确保后续所有阶段都在同一授权范围内工作。

## inputs
- `.lgwf/create_requirements.json` 中已确认的 `workflow_name=wf-dsl-upgrade`、`target_package_root=skills/lgwf-wf-tools/workflows/wf-dsl-upgrade`、`scope_mode`、`target_roots`、`target_workflow_lgwfs`、`include_workflow_ids`、`exclude_workflow_ids` 和 `max_targets` 输入语义。
- `.lgwf/business_flow.json` 中 `collect_targets` 阶段的 `objective`、`key_nodes`、`outputs` 与对下游 `batch_audit` 的 handoff。
- `04_confirm_business_flow/resources/scaffold_template_spec.md` 中关于 `wf/` 唯一 workflow root、两层 workflow 拓扑、`ws/.lgwf` 状态边界和 `internal_workflow_package` 默认 profile 的约束。
- `04_confirm_business_flow/resources/scaffold_result_contract.md` 中 `scaffold_plan` 需要覆盖 `create_dirs`、`create_files`、`placeholders` 和 `derived_from_business_flow` 的契约。
- `.lgwf/create_reference_context/dsl-assist/create-workflow.md` 与 `workflow-audit-checklist.md` 中关于根 workflow 只编排第一层子 workflow、禁止绝对路径与 `..`、子 workflow 自包含的规则。

## outputs
- `wf/01_collect_targets/workflow.lgwf` 的阶段设计草案，包含 `resolve_scope_mode`、`collect_registry_targets`、`collect_directory_targets`、`collect_file_targets`、`validate_target_paths` 和 `build_target_manifest` 节点的职责划分。
- 目标 package 的整体结构草案，至少说明根目录包含 `AGENTS.md`、`README.md`、`scripts/`、`tests/`、`ws/`、`wf/`、`wf/shared/scripts/`，以及根 `wf/workflow.lgwf` 将串联 `wf/01_collect_targets/` 到 `wf/08_summarize_upgrade_result/` 八个第一层子 workflow。
- 本阶段预期生成的结构化产物说明，至少覆盖 `target_manifest.json`、`target_scope_validation.json`、范围过滤摘要和授权边界说明。
- 本阶段所需的 `agents/`、`scripts/`、`resources/` 占位清单与它们在目标 package 中的建议位置。

## dependencies
- 依赖已确认的需求与业务流，不依赖其他步骤先落地真实代码。
- 本步骤是全部后续阶段的范围闸门；`execute-batch-audit` 及之后的步骤都只能消费它固化出的授权目标集合。
- 本步骤需要把 `scaffold_plan` 的顶层结构约束转成实现护栏，后续步骤不得重新发明根目录拓扑或新增孙级 workflow。

## implementation_suggestions
- 将目标 package 设计为 `internal_workflow_package`：生成根 `AGENTS.md`、`README.md`、`scripts/`、`tests/`、`ws/` 和 `wf/`，默认不生成根 `SKILL.md`。
- 根 `wf/workflow.lgwf` 只使用 `STEP ... WORKFLOW` 串联八个第一层子 workflow，不直接展开目标收集、audit 或 apply 细节。
- 在 `wf/01_collect_targets/scripts/` 中放置路径解析、registry 过滤、范围校验与清单汇总脚本；范围说明类文本放在 `wf/01_collect_targets/resources/`。
- 明确 `target_manifest.json` 中的所有目标路径都来自用户输入或 registry 解析结果，并经过相对/绝对路径合法性校验，避免后续阶段越权扫描。

## acceptance_notes
- 必须明确 `wf/` 是唯一 workflow root，目标 package 根目录禁止生成可运行 `workflow.lgwf`。
- 必须说明根 `wf/workflow.lgwf` 只编排 `01_collect_targets` 到 `08_summarize_upgrade_result` 八个第一层子 workflow，阶段内部逻辑全部下沉。
- 必须把 `scope_mode` 三种模式、`max_targets` 限制、registry 过滤和路径合法性校验作为本阶段的核心确认点。
- 必须强调 `ws/` 只是运行目录，运行状态只写入 `ws/.lgwf`，不会把 `.lgwf` 写回目标 package 源码树。

## out_of_scope
- `lgwf-wf-prompt-fix` 集成。
- `lgwf-wf-tools` facade 自动注册。
- 自动修复、自动重试和端到端业务运行保证。
- 直接产出完整 `workflow.lgwf` 实现内容。
