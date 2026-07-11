# define-shared-helper-and-verification

## step_slug
`define-shared-helper-and-verification`

## step_name
共享 helper、入口契约与最小验证基线

## goal
定义 package 级共享技术底座和验证边界，确保 `wf-dsl-upgrade` 在真正实现各阶段前就已经固定 `README.md`、`AGENTS.md`、`entry_contract.json`、`tests/` 和 `wf/shared/scripts/dsl_upgrade_common.py` 的职责分层、状态边界和最小验收命令。

## inputs
- 上游阶段或节点：
  - `.lgwf/business_flow.json` 中的整体业务流和 `downstream_step_inputs`
- 依赖文件或状态：
  - `docs_tmp/wf-dsl-upgrade-development.md`
  - `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md`
  - `.lgwf/create_reference_context/scaffold/scaffold_result_contract.md`
  - `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`
  - `.lgwf/create_reference_context/dsl-assist/create-workflow.md`
- 关键约束：
  - `package_profile=internal_workflow_package`
  - 根目录不生成 `SKILL.md`
  - 运行状态只允许写入 `ws/.lgwf`
  - 源码树不得保留 `.lgwf`、`__pycache__` 或运行输出

## outputs
- 预期生成的文件：
  - `AGENTS.md`
  - `README.md`
  - `entry_contract.json`
  - `tests/*.py`
  - `tests/README.md`
  - `wf/shared/scripts/dsl_upgrade_common.py`
  - `wf/03_upgrade_one_target/scripts/dsl_upgrade_common.py`
- 预期生成的目录：
  - `scripts/`
  - `tests/`
  - `ws/`
  - `wf/shared/scripts/`
- 交付给下游的结构片段：
  - 统一 JSON 读写、路径规范化、`allowed_dirs` 校验、hash、audit 调用封装和摘要裁剪
  - 覆盖 `dry_run`、`apply approve`、`apply reject`、越权保护、真实 audit、post-audit diff 的最小测试矩阵
  - 入口契约中对 `target_paths`、`allowed_dirs`、`mode`、`scope_mode`、`max_targets` 的权威约束

## dependencies
- 前置步骤：
  - 无
- 依赖节点：
  - 根 package 自包含契约和状态边界要求
  - 各阶段都会复用的共享技术能力
- 需要人工确认的位置：
  - 当前步骤本身不引入人工确认，但它定义的入口契约和验证基线应在 `confirm_step_designs` 时重点审查

## implementation_suggestions
- `wf/shared/scripts/dsl_upgrade_common.py` 只放稳定技术逻辑，不承载阶段私有 prompt、审批文案、计划规则或 summary 文案。
- 需要通过 `RUN_WORKFLOW` 独立快照执行的阶段，应在阶段 `scripts/` 内保留必要 helper，不能依赖父级 `wf/shared` 才能导入。
- `entry_contract.json` 保留 `scope_mode=registry` 契约，同时明确第一版优先实现 `explicit`；若 registry 只做保守支持，应在契约或 README 中清楚说明。
- `README.md`、`AGENTS.md` 和 `entry_contract.json` 的模块定位、入口、依赖、状态边界、产物、验证和禁止事项必须互相一致，避免文档漂移。
- 测试优先覆盖业务边界和结构约束，不依赖旧占位 sentinel；需要 fixture 时，也要避免重新把 `.lgwf` 或缓存目录写回源码树。

## acceptance_notes
- 重点确认共享 helper 没有吞并阶段私有业务判断，阶段规则仍留在各自目录。
- 重点确认验证命令至少覆盖 `lgwf.py audit wf/workflow.lgwf` 和 `python -m unittest discover ...`，并与开发文档一致。
- 重点确认根目录只保留源码、文档、测试和 `ws/`，不会重新生成旧占位实现里的运行态目录。

## out_of_scope
- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 把共享 helper 扩展成自由形式业务引擎
