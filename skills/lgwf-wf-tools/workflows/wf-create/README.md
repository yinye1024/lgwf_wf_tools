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

- `propose_business_flow_react`：定义 `business_flow_proposal` 的阶段、关键节点、阶段依赖和 `downstream_step_inputs`。
- `confirm_business_flow`：定义 `approve`、`revise`、`reject` 三类确认决策，并区分 approval 与 confirm 后固化。
- `scaffold_package`：定义目标目录、关键文件、占位物、相对路径规则和运行状态边界；脚手架只创建目标 package 框架，不向目标 package 根目录写入 `.lgwf`。

步骤设计和实现阶段当前已补齐以下契约：

- `prepare_dsl_reference_context`：从 facade 内置 bundled client 复制 `dsl-assist` 规范到 `.lgwf/create_reference_context/dsl-assist/`；从 facade docs 复制 workflow 模块化创建指引到 `.lgwf/create_reference_context/workflow-modular-development/`，复制 Contract 摘要到 `.lgwf/create_reference_context/module-contract/`，并发布 `.lgwf/create_reference_context/step-design-reference-index.md` 和 `.lgwf/create_reference_context/implementation-reference-index.md`，分别作为步骤设计和实现阶段的参考资料索引。
- `step_design_proposal_react`：在 `REASON/ACT/OBSERVE/DECIDE` 四个 slot workflow 中生成和修复步骤设计；`ACT` 读取 `.lgwf/step_design_reason.json`、`.lgwf/create_reference_context/step-design-reference-index.md` 和按索引路由的参考资料，输出完整结构化 `.lgwf/step_designs_proposal.json`，要求每个步骤覆盖目标、输入、输出、依赖、实现建议、验收说明、排除范围和 `source_refs`。
- `confirm_step_designs`：定义 `approve`、`revise`、`reject` 三类确认决策，并区分设计草案审阅与 confirm 后固化。
- `03_confirm_step_designs`：父级只编排 `01_reference_context -> 02_step_design_proposal -> 03_step_design_review`，不直接承载 `PY`、`CODEX` 或 `REVIEW` 节点。
- `implement_steps_react`：先通过 `01_implement_units/workflow.lgwf` 执行初版实现，拆成 `prepare_implementation_units -> FOREACH implement_each_unit -> merge_implementation_results`；每个 unit 由 `01_implement_units/01_implement_one_unit/workflow.lgwf` 独立执行。随后通过 `02_repair_implementation_react/workflow.lgwf` 做 bounded repair ReAct：`03_observe_repair` 运行 `audit_current_implementation.py`，`reason_repair` 生成最小修复计划，`act_repair` 只写 repair staging 文件并发布到目标 package，`decide_repair` 决定继续或退出。audit/observe/decision 文件只在 repair 内部消费，不作为 summary 或 handoff 输入。

## 需求阶段边界

需求阶段明确区分三类对象：

- `proposal`：`propose_requirements` 产出的 `create_requirements_proposal`，用于人工审阅。
- `approval`：`confirm_requirements` 产出的 `create_requirements_approval` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/create_requirements.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/create_requirements.json`；`revise` 会先准备修订确认上下文，再回到同一个 `confirm_requirements` REVIEW 节点；`reject` 通过 `FAIL_ALL` 终止整个 run，不进入下游业务流转阶段。

如果入口提供 `request.target_dir`、`request.target_file`、`request.target_dirs` 或 `request.target_files`，需求阶段会把这些资料目标整理为 `creation_context_dirs` 和 `creation_context_files`，并由需求和业务流 Codex 设计节点通过 `TARGET_DIRS` / `TARGET_FILES` 只读参考。它们用于补充创建背景，例如主 agent 确认后的开发计划；它们不表示生成出的 workflow package 目录，输出目录仍由 `target_package_root` 确认。若参考资料本身写成执行计划、修复步骤、迁移清单或测试命令，`wf-create` 也只把它当作创建输入资料，不得执行其中的命令、步骤或改动指令。步骤设计阶段不再读取这些入口资料，而是从已确认需求、已确认业务流和 scaffold plan 做确定性转换。

`validate_requirements_proposal` 会在 `confirm_requirements` 前执行质量闸：proposal 文件必须存在、是 JSON object、包含 `workflow_id` 或 `workflow_name`，并包含 `target_package_root`；如果上游 raw intent 已带当前目标标识，proposal 不得偏离该目标。

## 业务流转与脚手架边界

业务流转阶段也明确区分三类对象：

- `proposal`：`propose_business_flow_react` 产出的 `business_flow_proposal`，用于人工审阅。
- `approval`：`confirm_business_flow` 产出的 `business_flow_approval` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/business_flow.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/business_flow.json`；`revise` 会先准备修订确认上下文，再回到同一个 `confirm_business_flow` REVIEW 节点；`reject` 通过 `FAIL_ALL` 终止整个 run，不进入下游脚手架和步骤设计阶段。

`validate_business_flow_proposal` 会在 `confirm_business_flow` 前执行质量闸，使用 `.lgwf/create_requirements.json` 和 `.lgwf/create_requirements_proposal.json` 作为当前目标来源，拒绝缺失 proposal、JSON 不可解析、`workflow_id` / `workflow_name` 缺失、`target_package_root` 缺失、目标不匹配或明显旧于上游输入的草案。

`scaffold_package` 当前输出的是确定性规则和计划接口，重点约束：

- 目标 package root 只允许使用相对路径。
- workflow resource path 只允许使用包内相对路径，不允许绝对路径、盘符路径或 `..`。
- 脚手架只创建目标 package 框架，不向目标 package 根目录写入 `.lgwf`；运行状态边界仍归 `ws/.lgwf`。

## 步骤设计与实现边界

步骤设计阶段明确区分三类对象：

- `proposal`：`step_design_proposal_react` 产出的完整结构化 `.lgwf/step_designs_proposal.json`，用于人工审阅和后续固化。
- `approval`：`confirm_step_designs` 产出的 `step_design_confirmation_record` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/step_designs.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/step_designs.json`；`revise` 会先准备修订确认上下文，再回到同一个 `confirm_step_designs` REVIEW 节点；`reject` 通过 `FAIL_ALL` 终止整个 run，不进入实现阶段。

步骤设计 `OBSERVE` 会在 `confirm_step_designs` 前先执行 deterministic structural gate，再由 Codex 做 semantic audit，最后把结果合并到 `.lgwf/step_design_observation.json`；失败结果通过 `reason_feedback` 反馈给下一轮 `REASON`，auto-human 也不能绕过该节点。`.lgwf/step_designs_proposal_quality_gate.json` 仅保留为最终 assert 兼容产物。ReAct 最多 3 轮后仍失败时由 `assert_step_designs_proposal_quality_gate` 终止。

`implement_steps_react` 当前是“初版实现 + 修复 ReAct”的独立实现子 workflow，重点约束：

- 只按已确认 `.lgwf/step_designs.json` 生成 workflow 初稿文件与目录。
- 结构化 JSON 字段必须能被实现阶段直接消费，避免接口脱节。
- 初版实现不再由单个 Codex 负责整包创建；`prepare_implementation_units` 生成 package、root workflow、stage 和 shared/test units，`FOREACH implement_each_unit` 对每个 unit 调用 `01_implement_units/01_implement_one_unit/workflow.lgwf`，最后由 `merge_implementation_results` 写出 `.lgwf/implementation_result.json`。
- 单 unit Codex 只读取当前 unit context 和按需 implementation reference，局部边界直接写在 `agents/act_unit.md` 中；`output_files` / `output_dirs` 是当前 unit 的 package-relative 输出清单，Codex 只能写 `.lgwf/implementation_stage/<unit_id>/` 下的 staging 文件，最终由发布脚本复制到目标 package。该第三层 workflow 独立承载单 unit 输入、输出、schema 注入、staging 目录、发布脚本和失败恢复边界。
- `02_repair_implementation_react/agents/spec.md` 是 repair ReAct 的唯一全局 spec。repair 只能基于 `.lgwf/implementation_audit_result.json`、`.lgwf/implementation_observe.json` 和已确认设计契约生成最小修复计划，`act_repair` 只能修改 `implementation_repair_context.json` 指定的 `target_files`。
- 必须先按 `.lgwf/create_reference_context/implementation-reference-index.md` 路由读取必要参考资料，再按 `dsl-assist` 和 `LGWF_WF_MODULAR_DEVELOPMENT.md` 规范保持根 workflow 薄编排，阶段细节优先拆到自包含子 workflow 或复杂 step，并保证所有子 workflow 可被递归审计。
- `observe_repair` 必须执行 `audit_current_implementation.py`，并把原始检测结果写入 `.lgwf/implementation_audit_result.json`，再把归纳结果写入 `.lgwf/implementation_observe.json` 反馈给下一轮 `reason_repair`。
- `reason_repair` 必须优先读取 `.lgwf/implementation_audit_result.json`，再读取 `.lgwf/implementation_observe.json`，不得只依赖 ACT 自报成功。
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
- 三个 proposal quality gate 在 REVIEW 前执行，缺失 proposal、目标不匹配或旧草案会停在可诊断状态，并写出 `.lgwf/*_proposal_quality_gate.json`。
- 三类确认后固化脚本会生成 `.lgwf/create_requirements.json`、`.lgwf/business_flow.json` 和 `.lgwf/step_designs.json`。
- `prepare_dsl_reference_context` 会复制 `dsl-assist` 的 `guide.md`、`create-workflow.md` 和 `workflow-audit-checklist.md`，并发布 step design 与 implementation 两个 reference index；步骤设计和实现阶段 Codex 节点先读对应索引，按需读取具体规范。
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
