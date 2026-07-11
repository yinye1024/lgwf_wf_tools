# define-package-contracts

## step_slug

`define-package-contracts`

## step_name

顶层契约与入口边界

## goal

为 `wf-maintenance-gate` 确定顶层模块契约，补齐维护者和 runtime 都要依赖的入口文档与输入契约。这个步骤负责把目标 workflow 的定位、输入 schema、状态边界、产物边界和非目标写清楚，并把 `internal_workflow_package` 的根目录约束固定下来，避免实现阶段误生成根 `workflow.lgwf` 或根 `SKILL.md`。

## inputs

- 上游阶段或节点：
  - `.lgwf/business_flow.json` 中 `workflow_name`、`target_package_root`、`business_goal`
  - `docs_tmp/wf-maintenance-gate-development.md` 中的创建目标、非目标、输入输出建议和验收要求
- 依赖文件或状态：
  - `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md`
  - `.lgwf/create_reference_context/scaffold/scaffold_result_contract.md`
  - `.lgwf/create_reference_context/scaffold/scaffold_package_template.json`
  - `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`
  - `D:/allen/github/lgwf_wf_tools/skills/lgwf-wf-tools/workflows/01-share/module-contract.md`
- 关键约束：
  - `package_profile` 固定按默认值 `internal_workflow_package`
  - 目标 package root 固定为 `skills/lgwf-wf-tools/workflows/wf-maintenance-gate`
  - workflow root 只能是 `wf/`
  - 运行状态只能写入 `ws/.lgwf`
  - `entry_contract.json` 需要声明 `auto_human_policy=forbidden`

## outputs

- 预期生成的文件：
  - `AGENTS.md`
  - `README.md`
  - `entry_contract.json`
- 预期生成的目录：
  - `scripts/`
  - `tests/`
  - `ws/`
  - `wf/`
  - `wf/docs/steps/`
- 交付给下游的结构片段：
  - `maintenance_gate_request` 的输入 schema、默认字段和 `intent` / `verification_level` / `allow_*` 开关说明
  - `internal_workflow_package` 的根目录规则：不生成根 `SKILL.md`，不在根目录放可运行 `workflow.lgwf`
  - 顶层状态边界、产物边界、最小验证命令和禁止事项

## dependencies

- 前置步骤：
  - 无
- 依赖节点：
  - 已确认业务流中的总体业务目标和六个阶段边界
- 需要人工确认的位置：
  - 本步骤自身不引入人工确认；顶层输入契约中的 `allow_package_smoke`、`output_zip`、`auto_human_policy` 和非目标边界需要在 `acceptance_notes` 中作为审阅重点展示

## implementation_suggestions

- `AGENTS.md` 必须按 `lgwf_workflow_package` 契约写出模块定位、入口、依赖、状态边界、产物、验证和禁止事项，并明确它是 `registry.json` 管理的内部 workflow，不是独立 Codex skill。
- `README.md` 面向维护者说明用途、输入、六个阶段、可选验证项、产物位置和不会自动执行的事项，正文默认使用中文。
- `entry_contract.json` 应把 `maintenance_gate_request` 作为唯一入口对象，声明 `scope`、`changed_files`、`target_workflows`、`intent`、`verification_level`、`allow_deep_doctor`、`allow_workflow_tests`、`allow_pre_release`、`allow_package_smoke` 和 `output_zip`。
- `entry_contract.json` 的 `auto_human_policy` 固定为 `forbidden`，并把唯一运行状态目录声明为 `ws/.lgwf`，避免实现阶段把 `.lgwf` 写入源码树。
- 不要生成根 `SKILL.md`，也不要把 workflow 运行逻辑写进根文档；运行逻辑应下沉到 `wf/` 和各阶段私有资源。
- 在顶层契约中提前声明 `wf/artifact_contracts.json`、`ws/.lgwf/*.json` 和 `ws/reports/wf-maintenance-gate/report.md` 是后续步骤必须补齐的稳定产物。

## acceptance_notes

- 重点确认顶层 profile 是 `internal_workflow_package`，因此根目录不能生成 `SKILL.md`，也不能额外放一个可运行的根 `workflow.lgwf`。
- 重点确认 `entry_contract.json` 允许“显式给 changed_files”与“为空时自动采集 git 变更”两种模式，但都不允许直接把绝对路径或 `.lgwf` 路径写进业务输入。
- 重点确认 `output_zip` 只是可选参数，不代表 workflow 会在未确认时自动执行 package smoke 或覆盖现有 zip。
- 若需要在顶层文档中提到 vendor 刷新、registry 变更或发布动作，只能作为后续建议，不得写成自动行为。

## out_of_scope

- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 自动提交 git、自动发布 zip 或自动更新 `registry.json`
