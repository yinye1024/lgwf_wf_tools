# define-shared-helper-and-tests

## step_slug

`define-shared-helper-and-tests`

## step_name

共享 helper、测试矩阵与 smoke 基线

## goal

为 `wf-maintenance-gate` 建立跨阶段可复用的稳定技术层，集中承载文件分类规则、风险等级映射、命令计划拼装、结果归并辅助逻辑，以及最小但足够的测试矩阵。这个步骤的价值是避免把同一套路径规则、分类常量和报告枚举散落到多个阶段脚本里，同时保证新增 package 在实现后能满足开发文档列出的 focused tests 与最小 smoke 要求。

## inputs

- 上游阶段或节点：
  - `.lgwf/business_flow.json` 中六个阶段的输入输出和 handoff
  - `docs_tmp/wf-maintenance-gate-development.md` 中的分类规则、验证规则、验收要求
- 依赖文件或状态：
  - `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md`
  - `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`
  - `.lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md`
  - `D:/allen/github/lgwf_wf_tools/skills/lgwf-wf-tools/workflows/01-share/module-contract.md`
- 关键约束：
  - 共享目录只允许放稳定 Python helper，不能放阶段私有 prompt、approval 文案或 workflow DSL
  - 测试必须覆盖 impact classification、verification plan generation、registry/work_dir 路径和 artifact contract
  - 最小 smoke 只能验证“可生成 summary”，不能顺带修改源码或隐式打包

## outputs

- 预期生成的文件：
  - `wf/shared/scripts/maintenance_gate_common.py`
  - `tests/test_impact_classification.py`
  - `tests/test_verification_plan_generation.py`
  - `tests/test_registry_and_artifact_contracts.py`
  - `tests/test_wf_maintenance_gate_smoke.py`
  - `tests/README.md`
- 预期生成的目录：
  - `wf/shared/scripts/`
  - `tests/`
- 交付给下游的结构片段：
  - 文件分类类别、风险等级、推荐检查类型、summary status 的稳定枚举
  - 可供 `02_classify_impact`、`03_plan_verification`、`05_run_verification` 和 `06_summarize_gate_result` 复用的 helper API 边界
  - 针对 `maintenance_gate_summary.json`、`wf/artifact_contracts.json` 和 registry 路径的最小测试基线

## dependencies

- 前置步骤：
  - `define-package-contracts`
- 依赖节点：
  - 六个业务阶段都会复用同一套分类、风险、命令和状态枚举
- 需要人工确认的位置：
  - 当前步骤不单独引入人工确认；若共享 helper 计划承载阶段私有业务判断，应在审阅时判定为越界并要求收回到对应阶段

## implementation_suggestions

- 共享 helper 只放入跨阶段稳定逻辑，例如路径类别归类、风险等级映射、验证命令模板、summary status 判定辅助；不要把 `REVIEW` prompt、失败路由文案或阶段专用 JSON schema 写进共享脚本。
- `tests/test_impact_classification.py` 应覆盖 `facade_entry`、`workflow_source`、`workflow_tests`、`shared_contract`、`scripts`、`self_improve`、`vendor`、`docs_only` 和 `packaging` 这些类别的判定。
- `tests/test_verification_plan_generation.py` 应覆盖 `verification_level` 与 `allow_*` 开关的组合，尤其是 `allow_deep_doctor=false`、`allow_package_smoke=false` 时不得偷偷加入相应命令。
- `tests/test_registry_and_artifact_contracts.py` 应验证 registry 建议路径、`wf/workflow.lgwf`、`ws/.lgwf`、`ws/reports/wf-maintenance-gate/report.md` 和 `wf/artifact_contracts.json` 的契约一致性。
- `tests/test_wf_maintenance_gate_smoke.py` 应构造最小输入，验证在不修改源码的前提下能落出 `maintenance_gate_summary.json`，但不要求真实通过全部 doctor/pre-release。
- 如果确实需要根 `scripts/` 目录中的包级脚本，只能放稳定维护辅助脚本，不能与 `wf/<stage>/scripts/` 的阶段私有逻辑混用。

## 修订补充：共享规则表与测试清单

共享 helper 至少应暴露以下稳定数据结构，供分类、计划、执行和汇总阶段复用：

- `IMPACT_RULES`：路径模式到影响类别、优先级、风险和推荐检查的规则表。
- `COMMAND_TEMPLATES`：检查类型到命令、cwd、默认 timeout、写入副作用和开关依赖的模板表。
- `FAILURE_ROUTE_RULES`：失败类型到建议 workflow 的路由表。
- `STATUS_RULES`：命令结果到 `pass`、`fail`、`needs_review` 的归并规则。

`IMPACT_RULES` 的最小字段：

| 字段 | 含义 |
| --- | --- |
| `pattern` | 仓库相对路径 glob 或等价匹配规则 |
| `category` | `facade_entry`、`workflow_source`、`workflow_tests`、`shared_contract`、`scripts`、`self_improve`、`vendor`、`packaging`、`docs_only` |
| `priority` | 多规则命中时的排序依据，数值越高越优先 |
| `risk` | `low`、`medium`、`high` |
| `impacted_workflow_strategy` | `none`、`from_registry_path`、`all_workflows`、`self_improve` |
| `recommended_checks` | `doctor`、`deep_doctor`、`workflow_tests`、`self_improve_health`、`pre_release`、`package_smoke` 等候选 |

`COMMAND_TEMPLATES` 的最小字段：

| 字段 | 含义 |
| --- | --- |
| `check_id` | 稳定检查 id，例如 `doctor_basic`、`workflow_tests:<id>` |
| `command` | argv 数组，不用 shell 拼接字符串 |
| `cwd` | 固定为 facade 根或仓库根，不能依赖当前目录 |
| `timeout_seconds` | 默认超时，计划阶段可按等级调整 |
| `write_effects` | `.local/doctor/`、`.local/self-improve/`、`skills/lgwf-wf-tools/output/` 等目录 |
| `requires_allow` | 对应 `allow_deep_doctor`、`allow_pre_release`、`allow_package_smoke` 或空 |
| `short_circuit` | 失败后是否停止后续命令 |

测试清单必须覆盖以下断言：

- `docs_only` 只有在没有命中 `AGENTS.md`、`entry_contract.json`、`workflow.lgwf`、`registry.json`、`vendor/**` 等高优先级规则时才成立。
- `workflows/<id>/wf/**`、`workflows/<id>/entry_contract.json` 和 `workflows/<id>/AGENTS.md` 能映射到 registry 中的 `<id>`。
- `workflows/01-share/**` 和 `docs/LGWF_WF_MODULAR_DEVELOPMENT.md` 影响所有 workflow，风险为 `high`。
- `allow_deep_doctor=false`、`allow_pre_release=false`、`allow_package_smoke=false` 时，对应命令不得进入 `commands`，只能进入 `skipped_or_suggested_checks`。
- `output_zip` 已存在时，计划必须进入需要 REVIEW 决策的冲突状态，不得默认使用 `--force` 覆盖。
- 最小 smoke 只验证 summary 产物，不要求真实执行 deep doctor、pre-release 或 package smoke。

## acceptance_notes

- 重点确认共享 helper 不承载 prompt、approval prompt、阶段私有路径或 `.lgwf` 运行态写入。
- 重点确认 smoke test 只验证 gate 的最小闭环，不把 package smoke、真实 zip 输出或发布动作伪装成“测试必需”。
- 重点确认测试文件命名和断言内容与开发文档中的验收条目一一对应，避免“有测试文件但没覆盖真正风险”的情况。
- 若实现阶段发现共享 helper 需要知道某个阶段的内部 route 或 prompt 文案，应把这部分逻辑退回对应阶段目录，不继续扩张 shared 边界。

## out_of_scope

- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 在共享 helper 中直接执行 doctor、pre-release 或 zip 打包
