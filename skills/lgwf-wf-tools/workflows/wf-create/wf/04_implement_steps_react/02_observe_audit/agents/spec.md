# implement_steps_react 规格

## 职责

`implement_steps_react` 负责根据已确认的结构化步骤设计 JSON 生成目标 workflow package 的初稿文件与目录。它位于 `04_implement_steps_react/workflow.lgwf` 子 workflow 中，通过 ReAct 循环把实现、audit observe 和继续/退出决策拆开，确保 authoring audit 失败可以反馈给下一轮修复，但不承诺完整运行能力。

## 质量要求

- 实现阶段必须严格消费 `.lgwf/step_designs.json` 的结构化输入契约，不得脱离已确认设计自行扩 scope。
- 输出必须清楚对应到 workflow 初稿文件、目录和占位内容，而不是停留在抽象描述。
- `observe` 必须执行 authoring audit check，保留 `lgwf.py audit` 的 stdout/stderr、exit code 和失败项。
- `decide` 只根据 observe 结果决定继续修复或退出。
- 相对路径、work dir 边界和中文 UTF-8 文档基线必须继续成立。
- 当前阶段明确排除 `lgwf-wf-prompt-fix`、`lgwf-wf-tools`、自动修复和端到端运行保证。

## ReAct 共同准则

以下准则适用于 `reason`、`act` 和 `observe`。角色 prompt 只补充本节点职责，不重新定义这些边界。

### 稳定输入

- `.lgwf/step_designs.json` 是已确认步骤设计的权威输入；只消费已由 `confirm_step_designs` approve 后固化的 `.lgwf/step_designs.json` 或等价确认记录。
- `.lgwf/scaffold_package_result.json` 中的 `scaffold_plan` 是目录、文件和阶段 manifest 的结构事实源；业务 `stage_id` 不等于实际目录名，实际落位必须使用 `stage_manifest.stage_dir` 或 `create_files` 中的 `wf/<stage_dir>/workflow.lgwf`。
- `.lgwf/implementation_context.json` 是路径权威输入，包含 `workspace_root`、`target_package_root`、`target_package_abs`、`work_dir` 和路径使用规则。
- `.lgwf/implementation_audit_result.json` 是 OB Python 脚本写出的原始确定性检测结果；下一轮 reason 必须优先读取它。
- `.lgwf/implementation_observe.json` 是上一轮 observe 反馈；如果 `passed=false` 或 `audit.ok=false`，下一轮必须优先修复 audit 失败，不得扩展新范围。
- `.lgwf/create_reference_context/implementation-reference-index.md` 是实现阶段 DSL、audit 和模块化参考路由。需要创建或修复 `workflow.lgwf` 时先读该索引，再按需读取 `.lgwf/create_reference_context` 下的具体资料；这些资料只约束 DSL 语法、audit 修复和模块边界，不得改写 `.lgwf/step_designs.json` 的设计范围。
- `.lgwf/scaffold_package_result.json` 中的 `scaffold_plan` 已包含 package profile、目录结构、文件计划、placeholder 和阶段 manifest，判断 scaffold 结构时不得再读取源 resource 或旧 mirror。
- 不要读取 scaffold 源 resource 或旧 scaffold mirror；实现阶段只消费 `.lgwf/scaffold_package_result.json`。
- 单 unit 的 JSON 目标文件 schema 只允许来自 `.lgwf/current_implementation_unit_context.json.target_output_file_schemas`；如果当前 context 没有提供所需 schema，必须输出 `blocked_reason`，不得自行递归搜索 `.lgwf`、checkpoint、Codex stdout、human request、测试文件或宿主仓库样例来补 schema。

### 实现范围

- 只按已批准步骤覆盖的文件与目录生成 workflow 初稿，不得跳过结构化步骤设计直接发明额外需求或额外步骤。
- 按每个步骤设计中的 `step_slug`、`inputs`、`outputs`、`dependencies` 和 `implementation_suggestions` 落地文件。
- 记录生成范围、占位内容、剩余风险和已处理的 observe 反馈；输出不得停留在抽象描述。

### 路径与拓扑

- `.lgwf/implementation_context.json` 中的 `target_package_abs` 是最终目标包根目录，只供确定性脚本发布和 audit 使用；单 unit Codex 不直接写该目录。
- `target_package_root` 是 `workspace_root` 相对路径，不是当前运行目录 `work_dir` 相对路径。
- 禁止从 `work_dir` 使用 `..`、固定层级上跳或拼接 `plugins/...` 来猜测仓库根。
- 单 unit Codex 必须写入 `.lgwf/current_implementation_unit_context.json` 中的 `unit_output_dir`，并只生成 `workspace_output_files` 列出的 staging 文件。
- `.lgwf` 不是单 unit 的自由分析目录；除当前 handoff 显式列出的 context 文件和 `workspace_output_files` 中的 staging 草稿外，不得执行 `rg ... .lgwf`、`Get-ChildItem .lgwf -Recurse` 或读取其他运行态文件。
- 发布脚本会把 `unit_output_dir` 下的 package-relative 文件复制到 `target_package_abs`；不要先尝试 `work_dir/target_package_root` 或直接写最终目标目录。
- `workflow.lgwf` 只能生成在 `wf/workflow.lgwf` 或 `wf/<stage>/workflow.lgwf`，不得生成在目标 package 根目录。
- 不得生成 `wf/<stage>/<substage>/workflow.lgwf`。
- 根 `wf/workflow.lgwf` 只负责编排阶段；多个节点、人工确认、循环或修复逻辑必须下沉到 `wf/<stage>/workflow.lgwf`。
- `wf/<stage>/workflow.lgwf` 内部不得再通过 `STEP ... WORKFLOW` 引用孙级 workflow；阶段内复杂逻辑应在本文件内用 `PY`、`CODEX`、`REACT`、`APPROVAL`、`ROUTE` 编排。
- 每个 `wf/<stage>/` 目录保持自包含，拥有本阶段的 `workflow.lgwf`、`agents/`、`scripts/`、`resources/`。
- 不值得独立运行但需要独立说明和验收的内容应保留为结构化 `step_designs[]` 条目，或落到阶段私有 `resources/` 中；不得生成 `docs/steps/*.md` 或 `wf/docs/steps/*.md`。
- 根 `SKILL.md` 只允许在 `scaffold_plan.package_profile=skill_wrapped_workflow` 时生成；默认 `internal_workflow_package` 禁止生成根 `SKILL.md`。
- 所有 resource path 必须使用目标 package 内相对路径，不得使用绝对路径、盘符路径或 `..`。
- 运行状态边界仍归 `ws/.lgwf`；不得向目标 package 根目录写入 `.lgwf`。

### DSL 与 audit

- 不生成 `CODEX` / `PY` 节点中的裸 `INPUT state.*`，除非当前 DSL reference 明确允许该字段。
- `observe` 以脚本 audit 结果为准，不重新定义通过标准，不得把脚本 audit 的失败结果改写为通过。
- `decide` 优先根据 `.lgwf/implementation_audit_result.json` 的 `passed` 决定继续或退出，缺少该文件时才回退到 `.lgwf/implementation_observe.json`。

### 排除范围

- 不负责 `lgwf-wf-prompt-fix` 集成、`lgwf-wf-tools` 集成、自动修复、自动重试或端到端运行保证。
- 不生成 prompt 修复链路。
- 不生成 agent 化链路。

## 关键输入

- 已确认的 `.lgwf/step_designs.json`。
- 每个 `step_designs[]` 条目中的 `step_slug`、`stage_id`、`inputs`、`outputs`、`dependencies`、`implementation_suggestions`、`acceptance_notes` 和 `out_of_scope`。

## 预期输出

- workflow 初稿目录与文件。
- 对应的 `workflow.lgwf`、`agents/*.md`、`scripts/*.py`、`resources/`、`tests/` 或其他设计文档约定产物。
- 可供后续验收的初稿说明，而不是确认后正式运行状态 JSON。

## 边界

- 共同边界以“ReAct 共同准则”为准，角色 prompt 不再重复维护。
