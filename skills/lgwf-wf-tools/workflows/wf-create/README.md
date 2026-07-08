# lgwf-wf-create

`lgwf-wf-create` 用于根据用户原始意图创建一个新的 LGWF workflow 初稿。当前目录已经是 `lgwf-wf-tools/workflows/wf-create` 下的内部 workflow package：外层承载说明、测试和固定 `ws/`，真实 workflow package root 位于 `wf/`，由 facade 根目录 `registry.json` 以 `wf-create` 派发。

创建出的目标 workflow package 必须遵循 facade 共享的 [LGWF 工作流模块化创建指引](../../docs/LGWF_WF_MODULAR_DEVELOPMENT.md)：先确认 workflow、子 workflow、复杂 step 和目录边界，再落地入口文档、状态目录、产物和验证契约。

## 目标

- 固化 `collect_raw_intent` 到 `summarize_create_result` 的主流程阶段顺序。
- 提前锁定目录结构、节点命名和包内相对路径约束。
- 在需求、业务流、步骤设计和实现阶段持续应用 workflow 模块化边界。
- 为后续需求方案、业务流转、步骤设计和实现初稿阶段提供稳定落位点。

## 第一版范围

当前第一版只包含以下内容：

- `wf/workflow.lgwf` 主入口骨架。
- `wf/artifact_contracts.json` workspace 产物契约。
- `ws/` 工作目录边界约定。
- `collect_raw_intent`、`propose_requirements_react`、`confirm_requirements` 的需求阶段文档与接口约定。
- `propose_business_flow_react`、`confirm_business_flow` 的业务流转 proposal/approval 契约。
- `scaffold_package` 的确定性脚手架规则与最小验证入口。
- `design_steps_react` 的步骤设计文档 prompt 与规格。
- `docs/steps/*.md` 的字段模板、命名约定和实现阶段输入契约。
- `confirm_step_designs` 的确认模板与决策结构示例。
- `04_implement_steps_react` 的 ReAct 实现循环、audit observe 和边界说明。
- `05_enrich_contracts_react` 的 Contract 补强 ReAct 循环、Contract 文档检查和 audit observe。
- `dsl-assist` 创建与审计规范的运行时参考上下文。
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

1. `collect_raw_intent`
2. `propose_requirements_react`
3. `confirm_requirements`
4. `propose_business_flow_react`
5. `confirm_business_flow`
6. `scaffold_package`
7. `design_steps_react`
8. `confirm_step_designs`
9. `implement_steps_react`
10. `enrich_contracts_react`
11. `summarize_create_result`

其中需求阶段已经补齐以下契约：

- `collect_raw_intent`：允许用户从原始意图启动，不要求先手写完整结构化 JSON。
- `creation_context_dirs/files`：可由入口 `request.target_dir`、`request.target_file`、`request.target_dirs` 和 `request.target_files` 传入，作为需求、业务流和步骤设计阶段的只读创建资料。
- `propose_requirements_react`：定义 `create_requirements_proposal` 的关键字段、输出格式和设计理由。
- `confirm_requirements`：定义 `approve`、`revise`、`reject` 三类确认决策，并区分 approval 与 confirm 后固化。

业务流转与脚手架阶段当前已补齐以下契约：

- `propose_business_flow_react`：定义 `business_flow_proposal` 的阶段、关键节点、阶段依赖和 `downstream_step_inputs`。
- `confirm_business_flow`：定义 `approve`、`revise`、`reject` 三类确认决策，并区分 approval 与 confirm 后固化。
- `scaffold_package`：定义目标目录、关键文件、占位物、相对路径规则和运行状态边界；脚手架只创建目标 package 框架，不向目标 package 根目录写入 `.lgwf`。

步骤设计和实现阶段当前已补齐以下契约：

- `prepare_dsl_reference_context`：从 facade 内置 bundled client 复制 `dsl-assist` 规范到 `.lgwf/create_reference_context/dsl-assist/`，从 facade docs 复制 workflow 模块化创建指引到 `.lgwf/create_reference_context/workflow-modular-development/`，并复制 Contract 摘要到 `.lgwf/create_reference_context/module-contract/`，供后续 Codex 节点读取。
- `design_steps_react`：定义输出为 `docs/steps/*.md` 的可确认步骤设计文档草案，要求覆盖目标、输入、输出、依赖和实现建议。
- `confirm_step_designs`：定义 `approve`、`revise`、`reject` 三类确认决策，并区分设计草案审阅与 confirm 后固化。
- `implement_steps_react`：在独立子 workflow 中按 `reason -> act -> observe -> decide` 循环生成 workflow 初稿；`observe` 执行 authoring audit check，失败反馈回下一轮修复，同时明确不负责 prompt 修复、agent 化和自动修复。
- `enrich_contracts_react`：在独立子 workflow 中按 `reason -> act -> observe -> decide` 循环补齐目标 package 的模块 Contract；`observe` 同时检查 Contract 必备段落并运行 `lgwf.py audit`，只有全部通过才进入最终 package validation。

## 需求阶段边界

需求阶段明确区分三类对象：

- `proposal`：`propose_requirements_react` 产出的 `create_requirements_proposal`，用于人工审阅。
- `approval`：`confirm_requirements` 产出的 `create_requirements_approval` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/create_requirements.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/create_requirements.json`；`revise` 会回到修订确认点，`reject` 通过 `FAIL_ALL` 终止整个 run，不进入下游业务流转阶段。

如果入口提供 `request.target_dir`、`request.target_file`、`request.target_dirs` 或 `request.target_files`，需求阶段会把这些资料目标整理为 `creation_context_dirs` 和 `creation_context_files`，并由后续 Codex 设计节点通过 `TARGET_DIRS` / `TARGET_FILES` 只读参考。它们用于补充创建背景，例如主 agent 确认后的开发计划；它们不表示生成出的 workflow package 目录，输出目录仍由 `target_package_root` 确认。

## 业务流转与脚手架边界

业务流转阶段也明确区分三类对象：

- `proposal`：`propose_business_flow_react` 产出的 `business_flow_proposal`，用于人工审阅。
- `approval`：`confirm_business_flow` 产出的 `business_flow_approval` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/business_flow.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/business_flow.json`；`revise` 会回到修订确认点，`reject` 通过 `FAIL_ALL` 终止整个 run，不进入下游脚手架和步骤设计阶段。

`scaffold_package` 当前输出的是确定性规则和计划接口，重点约束：

- 目标 package root 只允许使用相对路径。
- workflow resource path 只允许使用包内相对路径，不允许绝对路径、盘符路径或 `..`。
- 脚手架只创建目标 package 框架，不向目标 package 根目录写入 `.lgwf`；运行状态边界仍归 `ws/.lgwf`。

## 步骤设计与实现边界

步骤设计阶段明确区分三类对象：

- `proposal`：`design_steps_react` 产出的 `docs/steps/*.md` 设计文档草案，用于人工审阅。
- `approval`：`confirm_step_designs` 产出的 `step_design_confirmation_record` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/step_designs.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/step_designs.json`；`revise` 会回到修订确认点，`reject` 通过 `FAIL_ALL` 终止整个 run，不进入实现阶段。

`implement_steps_react` 当前是独立 ReAct 子 workflow，重点约束：

- 只按已确认设计文档生成 workflow 初稿文件与目录。
- 设计文档字段必须能被实现阶段直接消费，避免接口脱节。
- 必须按 `dsl-assist` 和 `LGWF_WF_MODULAR_DEVELOPMENT.md` 规范保持根 workflow 薄编排，阶段细节优先拆到自包含子 workflow 或复杂 step，并保证所有子 workflow 可被递归审计。
- `observe` 必须执行 `lgwf.py audit` 类 authoring audit check，并把失败 stderr 写入 `.lgwf/implementation_observe.json` 反馈给下一轮 reason。
- `decide` 只根据 observe 的 audit 结果决定 `continue` 或 `exit`。

`enrich_contracts_react` 当前是独立 Contract 补强子 workflow，重点约束：

- 只补目标 package 的 `AGENTS.md`、`README.md` 等入口文档 Contract，不新增业务阶段或实现能力。
- Contract 必须覆盖模块定位、入口、依赖、状态边界、产物、验证和禁止事项。
- `observe` 必须执行 Contract 文档检查和 `lgwf.py audit`，失败时反馈给下一轮 Contract 修复。
- Contract 补强通过后，仍由 `validate_created_package` 执行最终确定性验收。
- 不负责 `lgwf-wf-prompt-fix` 自动调用、生成出的目标 workflow 自动接入 facade 路由、自动修复或端到端运行保证。

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
- `wf/artifact_contracts.json` 声明 `prepare_dsl_reference_context` 复制出的 `dsl-assist` workspace context 文件。
- 三个 approval 节点使用 `ROUTE_ON_DECISION`、`PERSIST` 和 `approve/revise/reject` 业务路由。
- proposal/实现阶段的 Codex 节点声明 `OUTPUT_JSON`，并与 prompt 输出契约一致。
- 三类确认后固化脚本会生成 `.lgwf/create_requirements.json`、`.lgwf/business_flow.json` 和 `.lgwf/step_designs.json`。
- `prepare_dsl_reference_context` 会复制 `dsl-assist` 的 `guide.md`、`create-workflow.md` 和 `workflow-audit-checklist.md`，设计和实现 Codex 节点显式读取这些规范。
- 需求阶段文档允许从原始意图进入，定义 proposal 字段和三类 approval 决策。
- 业务流转文档定义阶段、依赖、下游输入和三类 approval 决策。
- `scaffold_package` 规则和测试会拒绝绝对路径、盘符路径与 `..`，并明确不向目标 package 根目录写入 `.lgwf`。
- 步骤设计文档模板定义 `goal`、`inputs`、`outputs`、`dependencies`、`implementation_suggestions` 等字段，并与 `implement_steps_react` 输入契约一致。
- `confirm_step_designs` 模板支持三类决策。
- `implement_steps_react` 通过 `04_implement_steps_react/workflow.lgwf` 的 ReAct 循环生成 workflow 初稿，并把 authoring audit 失败反馈给下一轮修复；它仍不把 prompt 修复、agent 化和自动修复纳入当前范围。
- `summarize_create_result` 已定义未来运行时结果汇总接口，汇总内容只指向第一版结构性产物与验证入口，不宣称后续 workflow 已集成。
- `README.md` 与 `AGENTS.md` 明确写出 `wf/`、`ws/.lgwf` 边界，以及“不自动调用 `lgwf-wf-prompt-fix` / 不自动把生成出的目标 workflow 接入 facade 路由”。
- `README.md`、`AGENTS.md`、`tests/README.md` 和结果汇总脚本可按 UTF-8 正常读取，中文说明无乱码。

未覆盖范围：

- 需求确认、业务流转确认和步骤确认的真实运行。
- `lgwf-wf-prompt-fix` 自动调用、生成出的目标 workflow 自动接入 facade 路由、自动修复与端到端业务成功。
### revise 语义

`revise` 表示局部调整，不等同于 `reject`。需求、业务流和步骤设计三个确认点收到 `revise` 后，会进入对应 `revise_*` 人工确认点；主 agent 可以根据 `changes` 提交修订后的 `approve` 结果，workflow 随后固化修订产物并继续下游。`reject` 表示整体失败，通过 `FAIL_ALL` 终止整个 run。
