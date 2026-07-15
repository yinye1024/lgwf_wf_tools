# lgwf-wf-create

`lgwf-wf-create` 用于根据用户原始意图创建一个新的 LGWF workflow 初稿。当前目录已经是 `lgwf-wf-tools/workflows/wf-create` 下的内部 workflow package：外层承载说明、测试和固定 `ws/`，真实 workflow package root 位于 `wf/`，由 facade 根目录 `registry.json` 以 `wf-create` 派发。

创建出的目标 workflow package 必须遵循 facade 共享的 [LGWF 工作流模块化创建指引](../../docs/LGWF_WF_MODULAR_DEVELOPMENT.md)：先确认 workflow、子 workflow、复杂 step 和目录边界，再落地入口文档、状态目录、产物和验证契约。

## 目标

- 固化 `define_requirements` 到 `post_fix_handoff` 的主流程阶段顺序。
- 提前锁定目录结构、节点命名和包内相对路径约束。
- 在需求、业务流、步骤设计和实现阶段持续应用 workflow 模块化边界。
- 为后续需求方案、业务流转、步骤设计和实现初稿阶段提供稳定落位点。

## 第一版范围

当前第一版只包含以下内容：

- `wf/workflow.lgwf` 主入口骨架。
- `wf/artifact_contracts.json` workspace 产物契约。
- `ws/` 工作目录边界约定。
- `01_confirm_requirements` 的 raw intent、requirements proposal 和 requirements review 契约。
- `02_confirm_business_flow` 的 business flow proposal/review 和 scaffold package 契约。
- `scaffold_package` 的确定性脚手架规则与最小验证入口。
- `03_confirm_step_designs` 的步骤设计 ReAct slot workflow、prompt 和质量反馈契约。
- `.lgwf/step_designs_proposal.json` 的字段模板、命名约定和实现阶段输入契约。
- `confirm_step_designs` 的确认模板与决策结构示例。
- `04_implement_steps_react` 的初版 FOREACH 实现、repair ReAct 修复优化、内部 audit/observe 和边界说明。
- `07_post_fix_handoff` 的 wf-post-fix 人工确认交接阶段。
- `dsl-assist` 创建与审计规范的运行时参考上下文，以及步骤设计和实现阶段的按需读取索引。
- 中文 UTF-8 说明文档。

当前第一版不包含以下内容：

- `lgwf-wf-prompt-fix` 集成。
- 生成出的目标 workflow 自动接入 facade 路由、registry 或其他治理链路。
- 自动修复、自动重试或业务 happy path 保证。

## 目录约定

- package root：`skills/lgwf-wf-tools/workflows/wf-create`
- workflow package root：`wf/`
- workflow 入口：`wf/workflow.lgwf`
- work dir：`ws/`
- 运行状态目录：`ws/.lgwf`

不要把运行状态写到 package 根目录 `.lgwf`；本包固定使用同级 `ws/` 作为运行工作目录，运行状态只允许落在 `ws/.lgwf`。`wf/` 内也不得包含 `ws/` 或运行状态目录。

## 阶段骨架

主流程阶段已经固定为：

1. `define_requirements`
2. `design_structure`
3. `implement_draft`
4. `implement_steps_react`
5. `summarize_create_result`
6. `post_fix_handoff`

其中需求阶段已经补齐以下契约：

- `raw_intent`：允许用户从原始意图启动，不要求先手写完整结构化 JSON。
- `creation_context_dirs/files`：可由入口 `request.target_dir`、`request.target_file`、`request.target_dirs` 和 `request.target_files` 传入，作为需求和业务流阶段的只读创建资料；步骤设计阶段只消费已确认需求、已确认业务流和 scaffold plan。
- `requirements_proposal`：定义 `create_requirements_proposal` 的关键字段、输出格式和设计理由。
- `requirements_review`：定义 `approve`、`revise`、`reject` 三类确认决策，并区分 approval 与 confirm 后固化。

业务流转与脚手架阶段当前已补齐以下契约：

- `propose_business_flow`：通过单个 Codex 节点定义 `business_flow_proposal` 的阶段、关键节点、阶段依赖和 `downstream_step_inputs`。
- `confirm_business_flow`：定义 `approve`、`revise`、`reject` 三类确认决策，并区分 approval 与 confirm 后固化。
- `scaffold_package`：定义目标目录、关键文件、占位物、相对路径规则和运行状态边界；脚手架只创建目标 package 框架，不向目标 package 根目录写入 `.lgwf`。如果已确认需求明确目标是 Codex skill、包含根 `SKILL.md`，或列出 `scripts/`、`tests/`、`wf/shared/scripts/` 下的目标文件，脚手架会推断 `skill_wrapped_workflow` profile，并把这些语义必需文件写入 `create_files`。

步骤设计和实现阶段当前已补齐以下契约：

- `prepare_dsl_reference_context`：从 facade 内置 bundled client 复制 `dsl-assist` 规范到 `.lgwf/create_reference_context/dsl-assist/`；从 facade docs 复制 workflow 模块化创建指引到 `.lgwf/create_reference_context/workflow-modular-development/`，复制 Contract 摘要到 `.lgwf/create_reference_context/module-contract/`，并发布 `.lgwf/create_reference_context/step-design-reference-index.md` 和 `.lgwf/create_reference_context/implementation-reference-index.md`。其中 step design index 供步骤设计修复按需读取；implementation index 作为生成期参考产物保留，初版实现 Codex 不再读取该索引或整个 `.lgwf/create_reference_context` 目录。
- `step_design_proposal`：先由 `generate_step_designs` Python 节点确定性生成完整结构化 `.lgwf/step_designs_proposal.json`，要求覆盖 step、directory 和 file 三级设计；该节点读取 schema、passing example、动态 contract 和 scaffold `create_files`，不启动 Codex、不读取整个 reference context 目录，避免把步骤设计扩散成大范围资料读取任务。随后 Python 初检并进入修复 ReAct，`REASON CODEX` 读取 observation/decision 生成 `.lgwf/step_design_repair_plan.json`，`ACT CODEX` 执行修复，`OBSERVE PY` 验收，`DECIDE PY` 决定继续或退出。
- `step_design_validation_contract.required_stage_workflows` 是 stage workflow 的唯一 canonical 清单；`stage_aliases` 只用于归一化 business_flow/scaffold 的阶段命名，不得生成额外 `wf/<alias>/workflow.lgwf` 兼容文件。structural gate 会拒绝不在 required 清单中的 stage workflow target file，并要求 scaffold `create_files` 全量出现在 `file_designs` 和 `step_designs[].target_files` 中。
- `confirm_step_designs`：定义 `approve`、`revise`、`reject` 三类确认决策，并区分设计草案审阅与 confirm 后固化。
- `03_confirm_step_designs`：父级只编排 `01_reference_context -> 02_step_design_proposal -> 03_step_design_review`，不直接承载 `PY`、`CODEX` 或 `REVIEW` 节点。
- `implement_steps_react`：只以 `.lgwf/step_designs.json` 作为设计事实源，先通过 `01_implement_units/workflow.lgwf` 执行初版实现，拆成 `prepare_implementation_units -> FOREACH implement_each_unit -> merge_implementation_results`；每个 unit 由 `01_implement_units/01_implement_one_unit/workflow.lgwf` 独立执行。随后通过 `02_repair_implementation_react/workflow.lgwf` 做 bounded repair ReAct：`03_observe_repair` 运行 `audit_current_implementation.py`，`reason_repair` 生成最小修复计划，`act_repair` 只写 repair staging 文件并发布到目标 package，`decide_repair` 决定继续或退出。audit/observe/decision 文件只在 repair 内部消费，不作为 summary 或 handoff 输入。

## 需求阶段边界

需求阶段明确区分三类对象：

- `proposal`：`propose_requirements` 产出的 `create_requirements_proposal`，用于人工审阅。
- `approval`：`confirm_requirements` 产出的 `create_requirements_approval` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/create_requirements.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/create_requirements.json`；`revise` 会先准备修订确认上下文，再回到同一个 `confirm_requirements` REVIEW 节点；`reject` 通过 `FAIL_ALL` 终止整个 run，不进入下游业务流转阶段。

如果入口提供 `request.target_dir`、`request.target_file`、`request.target_dirs` 或 `request.target_files`，需求阶段会把这些资料目标整理为 `creation_context_dirs` 和 `creation_context_files`，并由需求和业务流 Codex 设计节点通过 `ANALYSIS_DIRS` / `ANALYSIS_FILES` 只读参考。它们用于补充创建背景，例如主 agent 确认后的开发计划；它们不表示生成出的 workflow package 目录，输出目录仍由 `target_package_root` 确认。若参考资料本身写成执行计划、修复步骤、迁移清单或测试命令，`wf-create` 也只把它当作创建输入资料，不得执行其中的命令、步骤或改动指令。步骤设计阶段不再读取这些入口资料，而是从已确认需求、已确认业务流和 scaffold plan 做确定性转换。

`validate_requirements_proposal` 会在 `confirm_requirements` 前执行质量闸：proposal 文件必须存在、是 JSON object、包含 `workflow_id` 或 `workflow_name`，并包含 `target_package_root`；如果上游 raw intent 已带当前目标标识，proposal 不得偏离该目标。

## 业务流转与脚手架边界

业务流转阶段也明确区分三类对象：

- `proposal`：`propose_business_flow` 产出的 `business_flow_proposal`，用于人工审阅。
- `approval`：`confirm_business_flow` 产出的 `business_flow_approval` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/business_flow.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/business_flow.json`；`revise` 会先准备修订确认上下文，再回到同一个 `confirm_business_flow` REVIEW 节点；`reject` 通过 `FAIL_ALL` 终止整个 run，不进入下游脚手架和步骤设计阶段。

`business_flow_proposal` 不再进入 ReAct 质量闸；该阶段只生成可审阅草案，结构合理性、待确认项和修订意见由后续 `confirm_business_flow` REVIEW 处理。

`scaffold_package` 当前输出的是确定性规则和计划接口，重点约束：

- 目标 package root 只允许使用相对路径。
- workflow resource path 只允许使用包内相对路径，不允许绝对路径、盘符路径或 `..`。
- 脚手架只创建目标 package 框架，不向目标 package 根目录写入 `.lgwf`；运行状态边界仍归 `ws/.lgwf`。
- `package_profile` 可由确认后的需求语义推断：目标为 Codex skill 或显式要求根 `SKILL.md` 时使用 `skill_wrapped_workflow`；内部 workflow package 才保持 `internal_workflow_package`。
- 确认需求中显式列出的 package 源文件，例如 `scripts/*.py`、`tests/*.py`、`wf/shared/scripts/*.py`，必须进入 `scaffold_plan.create_files`，后续步骤设计不得丢弃。

## 步骤设计与实现边界

步骤设计阶段明确区分三类对象：

- `proposal`：`step_design_proposal` 产出的完整结构化 `.lgwf/step_designs_proposal.json`，用于人工审阅和后续固化；该 proposal 包含 `directory_designs[]`、`file_designs[]` 和 `step_designs[]`，只描述文件结构和契约，不承载最终源码。
- `approval`：`confirm_step_designs` 产出的 `step_design_confirmation_record` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/step_designs.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/step_designs.json`；`revise` 会先准备修订确认上下文，再回到同一个 `confirm_step_designs` REVIEW 节点；`reject` 通过 `FAIL_ALL` 终止整个 run，不进入实现阶段。

步骤设计在首轮 `generate_step_designs` 确定性生成后会立即执行 structural gate，由 Python 直接写出 `.lgwf/step_design_structural_gate.json` 和 `.lgwf/step_design_observation.json`；不再启动 Codex 做首轮设计或语义审查读取大 JSON。失败结果以结构化 observation 和 decision 反馈给下一轮 `REASON CODEX`，由其生成详细修复方案 `.lgwf/step_design_repair_plan.json`；auto-human 也不能绕过该节点。ReAct 最多 3 轮后仍失败时由 `assert_step_designs_proposal_quality_gate` 基于 `.lgwf/step_design_observation.json` 终止。

`build_step_design_contract.py` 从 scaffold stage manifest 生成 canonical `required_stage_workflows`，再把 business_flow 的 stage id 合并为 canonical id 或 alias；当 scaffold 已经为某个 stage 给出数字前缀目录时，不再从 business stage id 推导第二套非数字 workflow。这样实现阶段只会拆分真实拓扑中的 workflow unit，避免生成未被根 workflow 引用、缺少私有脚本资源且无法通过 authoring audit 的兼容 workflow。

`implement_steps_react` 当前是“初版实现 + 修复 ReAct”的独立实现子 workflow，重点约束：

- 只按已确认 `.lgwf/step_designs.json` 生成 workflow 初稿文件与目录。
- 结构化 JSON 字段必须能被实现阶段直接消费，尤其是 `file_designs` 和 `directory_designs` 必须能作为 implementation unit 的文件结构依据，避免接口脱节。
- 初版实现不再由单个 Codex 负责整包创建；`prepare_implementation_units` 生成 package、root workflow、stage 和 shared/test units，`FOREACH implement_each_unit` 对每个 unit 调用 `01_implement_units/01_implement_one_unit/workflow.lgwf`，最后由 `merge_implementation_results` 写出 `.lgwf/implementation_result.json`。
- 单 unit Codex 只读取当前 unit context 和静态 DSL 写作约束，局部边界直接写在 `agents/act_unit.md` 中；`output_files` / `output_dirs` 是当前 unit 的 package-relative 输出清单，Codex 只能写 `.lgwf/implementation_stage/<unit_id>/` 下的 staging 文件，最终由发布脚本复制到目标 package。该第三层 workflow 独立承载单 unit 输入、输出、JSON schema 注入、静态 DSL 约束、staging 目录、发布脚本和失败恢复边界；`prepare_current_implementation_unit.py` 不再生成 DSL contract，防止把 DSL schema 维护在难以审查的脚本逻辑中。
- `02_repair_implementation_react/agents/spec.md` 是 repair ReAct 的唯一全局 spec。repair 只能基于 `.lgwf/implementation_audit_result.json`、`.lgwf/implementation_observe.json` 和已确认设计契约生成最小修复计划，`act_repair` 只消费 `.lgwf/implementation_repair_reason.json` 并只能修改其中 `target_files` 指定的文件。
- 创建或修改 `.lgwf` 文件时必须使用当前 unit context 和静态 DSL 写作约束作为输入，保持根 workflow 薄编排，阶段细节优先拆到自包含子 workflow 或复杂 step，并保证所有子 workflow 可被递归审计。
- `observe_repair` 必须执行 `audit_current_implementation.py`，并把确定性检测结果同时写入 `.lgwf/implementation_audit_result.json` 和 `.lgwf/implementation_observe.json`，反馈给下一轮 `reason_repair`。audit 结果保留根 `audit` 字段，同时通过 `workflow_audits` 收集每个 `wf/**/workflow.lgwf` 的 authoring audit 明细，避免递归 audit 在第一个子 workflow 语法错误处停止后只能一轮修一个文件。
- `reason_repair` 必须优先读取 `.lgwf/implementation_audit_result.json`，再读取 `.lgwf/implementation_observe.json`，不得只依赖 ACT 自报成功；如果 `workflow_audits` 暴露多个同类 `.lgwf` 语法错误，修复计划应合并同类目标文件。
- `decide_repair` 优先根据 `.lgwf/implementation_audit_result.json` 的 `passed` 决定 `continue` 或 `exit`，缺少该文件时才回退到 observe 结果；`.lgwf/implementation_decision.json` 只服务 repair ReAct 内部路由，不传给 summary 或 handoff。

## 结果交接边界

`summarize_create_result` 只负责写出创建结果汇总和报告；`post_fix_handoff` 由 `07_post_fix_handoff/workflow.lgwf` 独立承载，先运行 `prepare_post_fix_handoff` 生成 `.lgwf/post_fix_handoff_input.json` 和 `state.lgwf_wf_create.post_fix_handoff_payload`，再通过 `HANDOFF handoff_wf_post_fix` 暴露 pending action。该阶段只引导用户确认是否运行 `wf-post-fix`，不得自动启动下游 workflow。

## 文档与编码

- 中文 Markdown 默认使用 UTF-8。
- 代码标识符、配置键和 API 名称可以保留英文。
- workflow resource path 只允许使用包内相对路径。

## 最小验证

当前阶段建议从仓库根目录运行：

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

预期结果：

- `lgwf-wf-create` 的外层文件、`wf/`、`ws/`、测试目录和阶段目录存在。
- 根目录不包含 `workflow.lgwf` 或 `SKILL.md`，真实 workflow 入口只在 `wf/workflow.lgwf`。
- `wf/workflow.lgwf` 通过结构性 audit：只使用包内相对路径，并能观察到固定阶段顺序。
- `wf/artifact_contracts.json` 声明 `prepare_dsl_reference_context` 复制出的 `dsl-assist` workspace context 文件、`.lgwf/create_reference_context/step-design-reference-index.md` 和 `.lgwf/create_reference_context/implementation-reference-index.md` 索引文件。
- 三个 approval 节点使用 `ROUTE_ON_DECISION`、`PERSIST` 和 `approve/revise/reject` 业务路由。
- proposal/实现阶段的 Codex 节点声明 `OUTPUT_JSON`，并与 prompt 输出契约一致。
- 需求 proposal 和步骤设计 proposal 的 quality gate 在对应 REVIEW 前执行；业务流 proposal 由单个 Codex 节点产出，并交给后续人工 REVIEW 确认。
- 三类确认后固化脚本会生成 `.lgwf/create_requirements.json`、`.lgwf/business_flow.json` 和 `.lgwf/step_designs.json`。
- `prepare_dsl_reference_context` 会复制 `dsl-assist` 的 `guide.md`、`create-workflow.md` 和 `workflow-audit-checklist.md`，并发布 step design 与 implementation 两个 reference index；步骤设计修复节点可按 step design index 读取具体规范，初版实现 Codex 只依赖当前 unit context 和单 unit workflow 的静态 DSL 写作约束。
- 需求阶段文档允许从原始意图进入，定义 proposal 字段和三类 approval 决策。
- 业务流转文档定义阶段、依赖、下游输入和三类 approval 决策。
- `scaffold_package` 规则和测试会拒绝绝对路径、盘符路径与 `..`，并明确不向目标 package 根目录写入 `.lgwf`。
- 步骤设计文档模板定义 `goal`、`inputs`、`outputs`、`dependencies`、`implementation_suggestions` 等字段，并与 `implement_steps_react` 输入契约一致。
- `confirm_step_designs` 模板支持三类决策。
- `implement_steps_react` 通过 `04_implement_steps_react/workflow.lgwf` 先运行 `01_implement_units` 初版 FOREACH，再运行 `02_repair_implementation_react` 修复 ReAct；audit/observe/decision 是 repair 内部循环产物，不传给 summary 或 handoff；它仍不把 prompt 修复、agent 化和跨 workflow 自动修复纳入当前范围。
- `summarize_create_result` 和 `07_post_fix_handoff` 分别定义结果汇总与 wf-post-fix 人工交接接口，handoff 只暴露 pending action，不自动执行后续 workflow。
- `README.md` 与 `AGENTS.md` 明确写出 `wf/`、`ws/.lgwf` 边界，以及“不自动调用 `lgwf-wf-prompt-fix` / 不自动把生成出的目标 workflow 接入 facade 路由”。
- `README.md`、`AGENTS.md`、`tests/README.md` 和结果汇总脚本可按 UTF-8 正常读取，中文说明无乱码。

未覆盖范围：

- 需求确认、业务流转确认和步骤确认的真实运行。
- `lgwf-wf-prompt-fix` 自动调用、生成出的目标 workflow 自动接入 facade 路由、自动修复与端到端业务成功。
### revise 语义

`revise` 表示局部调整，不等同于 `reject`。需求、业务流和步骤设计三个确认点收到 `revise` 后，会运行对应 `prepare_*_revision_confirmation` 节点，把修订请求写回原确认节点的上下文，然后重新进入同一个 REVIEW 节点；主 agent 可以根据 `changes` 提交修订后的 `approve` 结果，workflow 随后固化产物并继续下游。`reject` 表示整体失败，通过 `FAIL_ALL` 终止整个 run。
