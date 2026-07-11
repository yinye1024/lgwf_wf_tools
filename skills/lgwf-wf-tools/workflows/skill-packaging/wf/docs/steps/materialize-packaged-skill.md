# materialize-packaged-skill

## step_slug
`materialize-packaged-skill`

## step_name
按确认计划执行受控打包

## goal
在已批准的 `confirmed_packaging_plan` 和明确覆盖许可范围内，通过稳定脚本执行目录复制、runtime 内置、runner/manifest 生成和执行摘要落盘，产出可继续校验的自包含 skill 打包结果。

## inputs
- 已确认业务流中 `04_materialize_packaged_skill` 阶段的目标、`key_nodes` 和向验证阶段交接的产物说明。
- `confirm-packaging-plan` 约定输出的 `confirmed_packaging_plan`、覆盖风险决策和兼容入口结论。
- `preflight-packaging-plan` 约定输出的复制排除规则、runner 计划、manifest 计划和 runtime 校验结论。
- 计划文档《skill-packaging 工作流创建意图与设计方案》中“当前状态”“创建目标”“目录设计建议”“实现策略建议”对复制逻辑和共享脚本复用的说明。
- `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md` 中关于 `internal_workflow_package`、`wf/` 唯一 workflow root、`wf/docs/steps/`、`wf/shared/scripts/` 和 `ws/.lgwf` 的结构要求。
- `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md` 中关于子 workflow 自包含、共享 helper 边界和状态目录隔离的规则。

## outputs
- 目标 package 内的 `wf/04_materialize_packaged_skill/workflow.lgwf`，在单个第一层子 workflow 内编排 `copy_source_skill_tree`、`embed_bundled_runtime`、`generate_local_runner`、`write_packaging_manifest` 和 `record_materialization_summary`。
- `wf/04_materialize_packaged_skill/agents/` 中用于解释执行摘要、占位范围或兼容入口策略的 prompt 或说明文档。
- `wf/04_materialize_packaged_skill/scripts/` 中实现真实复制、排除规则应用、runtime 内置、runner 生成、manifest 生成和执行摘要写入的确定性脚本。
- `wf/04_materialize_packaged_skill/resources/` 中只读模板、manifest 字段说明、runner 样板或打包规则说明。
- 跨阶段共享实现建议：如需复用当前脚本型能力，优先在 `wf/shared/scripts/packaging_common.py` 抽取稳定打包函数，再由本阶段脚本调用。
- 根 `wf/workflow.lgwf` 中对 `04_materialize_packaged_skill/workflow.lgwf` 的第四个阶段引用，并在同一轮实现中生成根 `AGENTS.md`、`README.md`、`entry_contract.json`、`tests/`、`ws/`、`wf/workflow.lgwf`、六个阶段目录和 `wf/docs/steps/*.md` 副本。
- 该阶段运行时产物约定：`.lgwf/materialized_package.json`、打包产物根目录、`vendor/lgwf-client-assist/`、`scripts/run_local_lgwf_workflow.py` 和 `PACKAGING_MANIFEST.json`。

## dependencies
- 依赖 `confirm-packaging-plan` 已形成唯一的 `confirmed_packaging_plan`；不得绕过确认节点直接执行真实写入。
- 依赖 `wf/docs/steps/*.md` 已在当前 run 被批准，后续实现时必须复制到目标 package 的 `wf/docs/steps/`，不能只留在 work dir。
- 为 `verify-packaged-skill` 提供打包后的输出目录、manifest 路径、runner 路径和执行摘要。

## implementation_suggestions
- 稳定动作优先放在确定性脚本，不让 Agent 直接承担复制、覆盖、manifest 生成或 runtime 嵌入的副作用实现。
- 将共享打包逻辑收敛到 `wf/shared/scripts/packaging_common.py` 或等价稳定 helper，避免 workflow 入口与兼容 CLI 逻辑分叉。
- 根 `wf/workflow.lgwf` 必须保持薄编排，只通过 `STEP ... WORKFLOW` 串联六个阶段；具体复制和文件生成逻辑全部下沉到本阶段子 workflow 内。
- 所有 authoring 和运行产物路径都必须遵守相对路径、禁止 `..` 和禁止向目标 package 根目录写 `.lgwf` 的规则。
- `implementation_result.generated_files` 后续应列出每个复制到目标 package 的 `wf/docs/steps/*.md` 文件和关键 source 文件，便于 `validate_created_package` 确定性验收。

## acceptance_notes
- 需要确认 facade 根 `scripts/package_lgwf_skill.py` 是保留为兼容薄包装器，还是完全由新 workflow 入口替代；当前草案倾向保留兼容入口但复用同一份共享 helper。
- 需要确认 `force=true` 的覆盖写入是否仅由本阶段读取上一阶段确认结果即可执行；当前草案不再增加新的写前审批节点。
- 根 `SKILL.md` 在当前 `package_profile=internal_workflow_package` 下不得生成；若未来改为 `skill_wrapped_workflow`，需要回到需求和脚手架确认补齐边界。
- 本阶段实现必须生成六个第一层阶段目录，并保证每个目录都有 `workflow.lgwf`、`agents/`、`scripts/`、`resources/`，不得用孙级 workflow 代替复杂逻辑。

## out_of_scope
- 不负责最终 audit 结论和失败修复。
- 不负责 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成、自动修复或自动重试。
- 不负责打包后 workflow 的端到端业务成功保证。

