# orchestrate-thin-root-workflow

## step_slug
`orchestrate-thin-root-workflow`

## step_name
根 workflow 薄编排与总产物契约

## goal
定义 `wf/workflow.lgwf` 和 `wf/artifact_contracts.json` 的控制面边界，让根 workflow 只表达 `01_collect_targets` 到 `04_summarize_upgrade_result` 的阶段顺序、条件分支和关键产物契约，不承载任何阶段私有脚本、prompt 或审批文案。

## inputs
- 上游阶段或节点：
  - `.lgwf/business_flow.json` 中的 `stages`、`stage_dependencies` 和 `downstream_step_inputs`
- 依赖文件或状态：
  - `docs_tmp/wf-dsl-upgrade-development.md`
  - `.lgwf/create_reference_context/dsl-assist/create-workflow.md`
  - `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md`
  - `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`
- 关键约束：
  - 根入口固定为 `wf/workflow.lgwf`
  - 根目录禁止生成可运行的 `workflow.lgwf`
  - 根 workflow 只通过 `STEP ... WORKFLOW "<stage>/workflow.lgwf"` 编排第一层子 workflow
  - `dry_run`、`reject`、无可自动修复项和 apply 跳过场景都必须进入 `04_summarize_upgrade_result`

## outputs
- 预期生成的文件：
  - `wf/workflow.lgwf`
  - `wf/artifact_contracts.json`
- 预期生成的目录：
  - 只引用既定第一层阶段目录，不新增孙级 workflow
- 交付给下游的结构片段：
- 根流程顺序：`01_collect_targets -> 02_confirm_scope -> FOREACH upgrade_each -> 04_summarize_upgrade_result`
- 条件分支：`02_confirm_scope` 后根据 `scope_approval` 进入 `FOREACH upgrade_each` 或直接进入 `04_summarize_upgrade_result`
- foreach 路径：`FOREACH upgrade_each` 对 `state.wf_dsl_upgrade.targets` 逐项运行 `03_upgrade_one_target/workflow.lgwf`，使用 `FAIL collect` 汇总每个 item 结果。

## dependencies
- 前置步骤：
  - `define-shared-helper-and-verification`
  - `collect-authorized-targets`
  - `confirm-scope`
  - `upgrade-one-target`
  - `summarize-upgrade-result`
- 依赖节点：
  - 根 workflow 中的范围收集、范围确认、FOREACH 单目标升级和结果汇总规则
- 需要人工确认的位置：
- 当前步骤本身不新增人工闸门；只消费 `02_confirm_scope` 的范围确认结论。

## implementation_suggestions
- 根 `wf/workflow.lgwf` 使用 `ENTRY FLOW main` 和命名 `FLOW main` 表达全局流程，不在根文件中展开任何阶段私有 `PY`、`CODEX`、`REVIEW` 细节。
- 以编号目录名作为根编排引用目标：`01_collect_targets`、`02_confirm_scope`、`03_upgrade_one_target`、`04_summarize_upgrade_result`。
- `02_confirm_scope` 的 `reject` 不应被设计成 `FAIL_ALL`；它应固化审批记录并把“跳过修复、继续汇总”的事实交给根 workflow 判断。
- 在 `wf/artifact_contracts.json` 中声明 `ws/.lgwf/*.json` 关键产物和 `ws/reports/wf-dsl-upgrade/report.md`，避免后续阶段依赖隐式临时文件。

## acceptance_notes
- 重点确认根 `stage_id` 采用目录名而不是业务流原始语义名，避免后续校验把 `collect_authorized_targets` 误解析为 `wf/collect_authorized_targets/`。
- 重点确认根 workflow 只承担控制面职责，所有目标收集、范围确认、单目标 audit/修复/复检和结果汇总逻辑都下沉到各阶段子 workflow。
- 重点确认 `dry_run`、`approve/apply`、`reject`、`skipped` 和 `partial` 路径都能流入总结阶段，不会因为审批分支设计错误提前失败。

## out_of_scope
- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复链路、自动重试或端到端运行保证
- 在本步骤中直接编写各阶段的完整脚本实现
