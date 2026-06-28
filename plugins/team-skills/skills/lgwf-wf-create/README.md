# lgwf-wf-create

`lgwf-wf-create` 用于根据用户原始意图创建一个新的 LGWF workflow 初稿。当前目录已经整理为类似 `lgwf-wf-agent/workflows/plan` 的内部 workflow package 形态：外层承载说明、测试和固定 `ws/`，真实 workflow package root 位于 `wf/`。

## 目标

- 固化 `collect_raw_intent` 到 `summarize_create_result` 的主流程阶段顺序。
- 提前锁定目录结构、节点命名和包内相对路径约束。
- 为后续需求方案、业务流转、步骤设计和实现初稿阶段提供稳定落位点。

## 第一版范围

当前第一版只包含以下内容：

- `wf/workflow.lgwf` 主入口骨架。
- `ws/` 工作目录边界约定。
- `collect_raw_intent`、`propose_requirements_react`、`confirm_requirements` 的需求阶段文档与接口约定。
- `propose_business_flow_react`、`confirm_business_flow` 的业务流转 proposal/approval 契约。
- `scaffold_package` 的确定性脚手架规则与最小验证入口。
- `design_steps_react` 的步骤设计文档 prompt 与规格。
- `docs/steps/*.md` 的字段模板、命名约定和实现阶段输入契约。
- `confirm_step_designs` 的确认模板与决策结构示例。
- `implement_steps_react` 的 workflow 初稿生成 prompt 与边界说明。
- 中文 UTF-8 说明文档。

当前第一版不包含以下内容：

- `lgwf-wf-prompt-fix` 集成。
- `lgwf-wf-agent` 集成。
- 自动修复、自动重试或业务 happy path 保证。

## 目录约定

- package root：`plugins/team-skills/skills/lgwf-wf-create`
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
10. `summarize_create_result`

其中需求阶段已经补齐以下契约：

- `collect_raw_intent`：允许用户从原始意图启动，不要求先手写完整结构化 JSON。
- `propose_requirements_react`：定义 `create_requirements_proposal` 的关键字段、输出格式和设计理由。
- `confirm_requirements`：定义 `approve`、`revise`、`reject` 三类确认决策，并区分 approval 与 confirm 后固化。

业务流转与脚手架阶段当前已补齐以下契约：

- `propose_business_flow_react`：定义 `business_flow_proposal` 的阶段、关键节点、阶段依赖和 `downstream_step_inputs`。
- `confirm_business_flow`：定义 `approve`、`revise`、`reject` 三类确认决策，并区分 approval 与 confirm 后固化。
- `scaffold_package`：定义目标目录、关键文件、占位物、相对路径规则和运行状态边界；脚手架只创建目标 package 框架，不向目标 package 根目录写入 `.lgwf`。

步骤设计和实现阶段当前已补齐以下契约：

- `design_steps_react`：定义输出为 `docs/steps/*.md` 的可确认步骤设计文档草案，要求覆盖目标、输入、输出、依赖和实现建议。
- `confirm_step_designs`：定义 `approve`、`revise`、`reject` 三类确认决策，并区分设计草案审阅与 confirm 后固化。
- `implement_steps_react`：定义如何按已确认设计生成 workflow 初稿文件与目录，同时明确不负责 prompt 修复、agent 化和自动修复。

## 需求阶段边界

需求阶段明确区分三类对象：

- `proposal`：`propose_requirements_react` 产出的 `create_requirements_proposal`，用于人工审阅。
- `approval`：`confirm_requirements` 产出的 `create_requirements_approval` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/create_requirements.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/create_requirements.json`；`revise` 和 `reject` 不进入下游业务流转阶段。

## 业务流转与脚手架边界

业务流转阶段也明确区分三类对象：

- `proposal`：`propose_business_flow_react` 产出的 `business_flow_proposal`，用于人工审阅。
- `approval`：`confirm_business_flow` 产出的 `business_flow_approval` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/business_flow.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/business_flow.json`；`revise` 和 `reject` 不进入下游脚手架和步骤设计阶段。

`scaffold_package` 当前输出的是确定性规则和计划接口，重点约束：

- 目标 package root 只允许使用相对路径。
- workflow resource path 只允许使用包内相对路径，不允许绝对路径、盘符路径或 `..`。
- 脚手架只创建目标 package 框架，不向目标 package 根目录写入 `.lgwf`；运行状态边界仍归 `ws/.lgwf`。

## 步骤设计与实现边界

步骤设计阶段明确区分三类对象：

- `proposal`：`design_steps_react` 产出的 `docs/steps/*.md` 设计文档草案，用于人工审阅。
- `approval`：`confirm_step_designs` 产出的 `step_design_confirmation_record` 决策结构，记录 `approve`、`revise`、`reject`。
- `confirmed artifact`：未来运行时在用户确认后固化的 `.lgwf/step_designs.json`，对应“确认后固化”产物。

`approve` 后会把确认结果固化为 `.lgwf/step_designs.json`；`revise` 和 `reject` 不进入实现阶段。

`implement_steps_react` 当前输出的是 workflow 初稿生成接口，重点约束：

- 只按已确认设计文档生成 workflow 初稿文件与目录。
- 设计文档字段必须能被实现阶段直接消费，避免接口脱节。
- 不接入 `lgwf-wf-prompt-fix`、`lgwf-wf-agent`、自动修复或端到端运行保证。

## 文档与编码

- 中文 Markdown 默认使用 UTF-8。
- 代码标识符、配置键和 API 名称可以保留英文。
- workflow resource path 只允许使用包内相对路径。

## 最小验证

当前阶段建议从仓库根目录运行：

```powershell
python -m unittest discover plugins\team-skills\skills\lgwf-wf-create\tests
```

预期结果：

- `lgwf-wf-create` 的外层文件、`wf/`、`ws/`、测试目录和阶段目录存在。
- 根目录不包含 `workflow.lgwf` 或 `SKILL.md`，真实 workflow 入口只在 `wf/workflow.lgwf`。
- `wf/workflow.lgwf` 通过结构性 audit：只使用包内相对路径，并能观察到固定阶段顺序。
- 三个 approval 节点使用 `ROUTE_ON_DECISION`、`PERSIST` 和 `approve/revise/reject` 业务路由。
- proposal/实现阶段的 Codex 节点声明 `OUTPUT_JSON`，并与 prompt 输出契约一致。
- 三类确认后固化脚本会生成 `.lgwf/create_requirements.json`、`.lgwf/business_flow.json` 和 `.lgwf/step_designs.json`。
- 需求阶段文档允许从原始意图进入，定义 proposal 字段和三类 approval 决策。
- 业务流转文档定义阶段、依赖、下游输入和三类 approval 决策。
- `scaffold_package` 规则和测试会拒绝绝对路径、盘符路径与 `..`，并明确不向目标 package 根目录写入 `.lgwf`。
- 步骤设计文档模板定义 `goal`、`inputs`、`outputs`、`dependencies`、`implementation_suggestions` 等字段，并与 `implement_steps_react` 输入契约一致。
- `confirm_step_designs` 模板支持三类决策。
- `implement_steps_react` 只声明生成 workflow 初稿文件，不把 prompt 修复、agent 化和自动修复纳入当前范围。
- `summarize_create_result` 已定义未来运行时结果汇总接口，汇总内容只指向第一版结构性产物与验证入口，不宣称后续 workflow 已集成。
- `README.md` 与 `AGENTS.md` 明确写出 `wf/`、`ws/.lgwf` 边界，以及“不接入 `lgwf-wf-prompt-fix` / `lgwf-wf-agent`”。
- `README.md`、`AGENTS.md`、`tests/README.md` 和结果汇总脚本可按 UTF-8 正常读取，中文说明无乱码。

未覆盖范围：

- 需求确认、业务流转确认和步骤确认的真实运行。
- `lgwf-wf-prompt-fix`、`lgwf-wf-agent`、自动修复与端到端业务成功。
### revise 语义

`revise` 表示局部调整，不等同于 `reject`。需求、业务流和步骤设计三个确认点收到 `revise` 后，会进入对应 `revise_*` 人工确认点；主 agent 可以根据 `changes` 提交修订后的 `approve` 结果，workflow 随后固化修订产物并继续下游。`reject` 才表示整体不继续，直接进入结果汇总。
