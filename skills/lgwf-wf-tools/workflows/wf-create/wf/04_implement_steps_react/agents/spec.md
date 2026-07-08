# implement_steps_react 规格

## 职责

`implement_steps_react` 负责根据已确认的步骤设计文档生成目标 workflow package 的初稿文件与目录。它位于 `04_implement_steps_react/workflow.lgwf` 子 workflow 中，通过 ReAct 循环把实现、audit observe 和继续/退出决策拆开，确保 authoring audit 失败可以反馈给下一轮修复，但不承诺完整运行能力。

## 质量要求

- 实现阶段必须严格消费 `docs/steps/*.md` 的输入契约，不得脱离已确认设计自行扩 scope。
- 输出必须清楚对应到 workflow 初稿文件、目录和占位内容，而不是停留在抽象描述。
- `observe` 必须执行 authoring audit check，保留 `lgwf.py audit` 的 stdout/stderr、exit code 和失败项。
- `decide` 只根据 observe 结果决定继续修复或退出。
- 相对路径、work dir 边界和中文 UTF-8 文档基线必须继续成立。
- 当前阶段明确排除 `lgwf-wf-prompt-fix`、`lgwf-wf-tools`、自动修复和端到端运行保证。

## ReAct 共同准则

以下准则适用于 `reason`、`act` 和 `observe`。角色 prompt 只补充本节点职责，不重新定义这些边界。

### 稳定输入

- `.lgwf/step_designs.json` 是已确认步骤设计的权威输入；只消费已由 `confirm_step_designs` approve 后固化的 `.lgwf/step_designs.json` 或等价确认记录。
- `.lgwf/implementation_context.json` 是路径权威输入，包含 `workspace_root`、`target_package_root`、`target_package_abs`、`work_dir` 和路径使用规则。
- `.lgwf/implementation_observe.json` 是上一轮 observe 反馈；如果 `passed=false` 或 `audit.ok=false`，下一轮必须优先修复 audit 失败，不得扩展新范围。
- `.lgwf/create_reference_context/dsl-assist/*.md` 是 LGWF DSL 创建、审计和 workflow 拆分规范。
- `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md` 和 `.lgwf/create_reference_context/scaffold/scaffold_package_template.json` 是 package profile、目录结构和文件计划的脚手架规范。
- `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md` 是 workflow、子 workflow、复杂 step、目录边界、状态隔离和验证入口的总纲。
- 不要从 `ws/02_confirm_business_flow/resources/...` 读取 scaffold 资源；Codex 子进程的 workspace root 是 `ws/`，scaffold 资源已由 `prepare_dsl_reference_context` 镜像到 `.lgwf/create_reference_context/scaffold/`。

### 实现范围

- 只按已批准步骤覆盖的文件与目录生成 workflow 初稿，不得跳过设计文档直接发明额外需求或额外步骤。
- 按每个步骤设计中的 `step_slug`、`inputs`、`outputs`、`dependencies` 和 `implementation_suggestions` 落地文件。
- 记录生成范围、占位内容、剩余风险和已处理的 observe 反馈；输出不得停留在抽象描述。

### 路径与拓扑

- 读写目标包时必须使用 `.lgwf/implementation_context.json` 中的 `target_package_abs` 作为唯一目标包写入根目录。
- `target_package_root` 是 `workspace_root` 相对路径，不是当前运行目录 `work_dir` 相对路径。
- 禁止从 `work_dir` 使用 `..`、固定层级上跳或拼接 `plugins/...` 来猜测仓库根。
- 如 `target_package_abs` 不存在，应直接创建该目录；不要先尝试 `work_dir/target_package_root`。
- 必须先创建目标 package 内的 `wf/docs/steps/`，再复制当前 run 的已批准步骤设计文档；不得只在 `work_dir/docs/steps/` 保留文档。
- `implementation_result.generated_files` 必须列出每个复制后的 `wf/docs/steps/*.md` 文件，便于 `validate_created_package` 做确定性验收。
- `workflow.lgwf` 只能生成在 `wf/workflow.lgwf` 或 `wf/<stage>/workflow.lgwf`，不得生成在目标 package 根目录。
- 不得生成 `wf/<stage>/<substage>/workflow.lgwf`。
- 根 `wf/workflow.lgwf` 只负责编排阶段；多个节点、人工确认、循环或修复逻辑必须下沉到 `wf/<stage>/workflow.lgwf`。
- `wf/<stage>/workflow.lgwf` 内部不得再通过 `STEP ... WORKFLOW` 引用孙级 workflow；阶段内复杂逻辑应在本文件内用 `PY`、`CODEX`、`REACT`、`APPROVAL`、`ROUTE` 编排。
- 每个 `wf/<stage>/` 目录保持自包含，拥有本阶段的 `workflow.lgwf`、`agents/`、`scripts/`、`resources/`。
- 不值得独立运行但需要独立说明和验收的内容应保留为复杂 step，并在 `wf/docs/steps/*.md` 或阶段私有 `resources/` 中写明目标、输入、输出、依赖、验证和禁止事项。
- 根 `SKILL.md` 只允许在 `scaffold_plan.package_profile=skill_wrapped_workflow` 时生成；默认 `internal_workflow_package` 禁止生成根 `SKILL.md`。
- 所有 resource path 必须使用目标 package 内相对路径，不得使用绝对路径、盘符路径或 `..`。
- 运行状态边界仍归 `ws/.lgwf`；不得向目标 package 根目录写入 `.lgwf`。

### DSL 与 audit

- 不生成 `CODEX` / `PY` 节点中的裸 `INPUT state.*`，除非当前 DSL reference 明确允许该字段。
- `observe` 以脚本 audit 结果为准，不重新定义通过标准，不得把脚本 audit 的失败结果改写为通过。
- `decide` 只根据 `.lgwf/implementation_observe.json` 的 `passed` 决定继续或退出。

### 排除范围

- 不负责 `lgwf-wf-prompt-fix` 集成、`lgwf-wf-tools` 集成、自动修复、自动重试或端到端运行保证。
- 不生成 prompt 修复链路。
- 不生成 agent 化链路。

## 关键输入

- 已确认的步骤设计文档。
- 每份文档中的 `step_slug`、`inputs`、`outputs`、`dependencies`、`implementation_suggestions`。

## 预期输出

- workflow 初稿目录与文件。
- 对应的 `workflow.lgwf`、`agents/*.md`、`scripts/*.py`、`resources/`、`tests/` 或其他设计文档约定产物。
- 可供后续验收的初稿说明，而不是确认后正式运行状态 JSON。

## 边界

- 共同边界以“ReAct 共同准则”为准，角色 prompt 不再重复维护。
