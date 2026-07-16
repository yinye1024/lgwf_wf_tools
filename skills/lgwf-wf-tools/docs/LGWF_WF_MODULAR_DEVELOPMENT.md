# LGWF 工作流模块化创建指引

本文把 `LGWF_MODULAR_DEVELOPMENT.md` 中的模块边界思想转译为 LGWF workflow 的创建规范。它用于指导新建、转换、修复和优化 workflow package，尤其约束当前创建入口 `wf-create-fast` 的需求确认、业务流确认、scaffold 落盘和主 agent handoff 阶段。

核心原则是：目录是边界，契约是接口，状态不穿透，子流程尽量自包含。

## 适用范围

- 新建 `lgwf_workflow_package`。
- 把 prompt workflow 转换为 LGWF workflow package。
- 为现有 workflow 拆分子 workflow、阶段目录或复杂 step。
- 修复 workflow 时调整目录、prompt、script、schema、状态目录和验证入口。
- 给 workflow package 补齐 `AGENTS.md`、`README.md`、`entry_contract.json` 或局部 step 文档。

只调整单个 prompt 文案、单个脚本 bug 或单个测试 fixture 时，可以只按目标模块的局部规范执行；一旦涉及目录结构、子 workflow 拆分、状态边界或入口契约，必须回到本文。

## 模块层级

LGWF workflow 创建时按三层看待模块。

| 层级 | 目录边界 | 适用场景 | 必备契约 |
| --- | --- | --- | --- |
| workflow package | `<package>/` 或 `workflows/<id>/` | 一个稳定用户意图或可派发 workflow | `AGENTS.md`、`README.md`、入口、状态边界、产物、验证、禁止事项 |
| 子 workflow | `wf/<stage>/` 或 `wf/<stage>/<subflow>/` | 可独立理解、可恢复、可验证的业务阶段或阶段内部业务子流程 | `workflow.lgwf`、阶段私有 `agents/` / `scripts/` / `resources/`、输入输出说明 |
| 复杂 step | `wf/docs/steps/*.md` 或 `wf/<stage>/resources/<step>/` | 不值得独立运行，但需要独立说明和验收的步骤 | 目标、输入、输出、依赖、产物、验证和禁止事项 |

子 workflow 是强模块，复杂 step 是弱模块。弱模块一旦出现独立输入输出、独立人工确认、独立恢复或跨 workflow 复用需求，应升级为子 workflow。
孙级 workflow 也是子 workflow，但只能作为阶段内部的受控业务子流程使用；它必须有明确职责、显式输入输出和父级编排边界，不得只是为了按文件类型拆目录。

## 推荐目录

默认使用“外层 package + 内层 `wf/` workflow root”的结构：

```text
<workflow-package>/
  AGENTS.md
  README.md
  entry_contract.json
  scripts/
  tests/
  ws/
  wf/
    workflow.lgwf
    artifact_contracts.json
    docs/
      steps/
    shared/
      scripts/
    <stage>/
      workflow.lgwf
      agents/
      scripts/
      resources/
      <subflow>/
        workflow.lgwf
        agents/
        scripts/
        resources/
```

`wf/` 是唯一 workflow package root，真实入口固定为 `wf/workflow.lgwf`。外层 package 根目录不得再放可运行的 `workflow.lgwf`。`ws/` 与 `wf/` 同级，只作为 LGWF work dir，运行状态只允许写入 `ws/.lgwf/`。

## 拆分准则

满足以下任一条件时，优先拆为子 workflow：

- 该阶段有独立业务目标，能用一句话说明“负责什么”。
- 该阶段有独立输入、输出、产物或验收标准。
- 该阶段包含人工确认、review、handoff 或独立风险边界。
- 该阶段失败后需要单独 resume、重跑或诊断。
- 该阶段可能被其他 workflow 复用。
- 该阶段内部 prompt、script、schema、resource 已经成体系。

满足以下任一条件时，可以在阶段内部继续拆为孙级 workflow：

- 阶段内部存在两个以上职责清楚的业务子流程，且每个子流程都有独立输入、输出、确认点或失败恢复边界。
- 父阶段 workflow 继续承载所有节点会导致控制面过长，难以看出业务流转顺序。
- 子流程需要把自己的 prompt、script、schema、review prompt 和资源封装在同一目录，避免 Codex 节点读取过宽上下文。
- 子流程的产物会作为父阶段内部的显式 handoff artifact，被后续子流程消费。

满足以下条件时，保留为复杂 step：

- 它只是当前阶段内部的连续动作。
- 产物只服务当前阶段，不需要独立派发或恢复。
- 拆成子 workflow 后输入输出契约比业务本身更复杂。
- 它没有独立人工确认点，也不会被其他 workflow 复用。

禁止为了“看起来模块化”而把每个节点都拆成子 workflow。模块边界应服务理解、恢复、验证和复用。
孙级 workflow 的命名必须表达业务职责，可以使用数字前缀表达阶段内顺序，例如 `01_raw_intent`、`02_requirements_proposal`、`03_requirements_review`；禁止使用 `scripts`、`agents`、`resources`、`helpers` 这类文件类型名称作为 workflow 边界。

## 子 workflow 自包含要求

一个 `wf/<stage>/` 或 `wf/<stage>/<subflow>/` 目录应自包含该阶段或子流程的私有资源：

- `workflow.lgwf`：阶段内部拓扑。
- `agents/`：阶段私有 prompt、spec、reason、act、observe 等文档。
- `scripts/`：阶段私有脚本。
- `resources/`：阶段私有模板、schema、确认文案、示例和只读资料。
- 必要时补充 `README.md`，说明阶段定位、输入、输出、状态、验证和禁止事项。

父 workflow 只通过 `STEP ... WORKFLOW "<stage>/workflow.lgwf"` 或明确 handoff payload 调用子 workflow，不读取子 workflow 的内部临时文件作为隐式接口。

阶段 workflow 可以继续通过 `STEP ... WORKFLOW "<subflow>/workflow.lgwf"` 调用孙级 workflow，但必须满足以下约束：

- 父阶段 `workflow.lgwf` 只负责编排子流程顺序、route、handoff 和父级状态流，不直接读取孙级内部临时文件作为隐式接口。
- 每个孙级 workflow 的目录名、`README.md` 或本地说明必须写清一句话职责、输入、输出、依赖、产物、验证和禁止事项。
- 孙级 workflow 只能再包含节点、prompt、script、resource 和复杂 step；默认不得继续创建更深层 `workflow.lgwf`。确需第三层以上嵌套时，必须先在父级步骤设计中说明为什么两层无法表达职责边界。
- 同一层级的子流程之间只能通过 confirmed artifact、handoff payload、report 或父级声明的 workspace/state 字段交接，不得互相读取对方目录下的私有 prompt、script 或运行中临时文件。

## 复杂 step 自包含要求

复杂 step 可以落在 `wf/docs/steps/*.md`，也可以落在阶段私有 `resources/` 下。每个 step 文档至少说明：

- `目标`：本 step 解决什么问题。
- `输入`：读取哪些 state 字段、文件、confirmed artifact 或上游产物。
- `输出`：写入哪些 state 字段、文件、报告或 handoff payload。
- `依赖`：依赖的 prompt、script、schema、共享 helper 或外部资料。
- `验证`：如何确定 step 结果可用。
- `禁止事项`：不得读写的目录、不得绕过的确认、不得扩大到的任务。

步骤设计阶段生成的 `docs/steps/*.md` 必须能被实现阶段直接消费，不能只写抽象描述。

## 控制面与执行面

`workflow.lgwf` 是控制面，只表达拓扑、状态流、route、approval、handoff 和子 workflow 调用。复杂业务判断、prompt 语义、脚本逻辑、schema 和模板应下沉到对应目录。

对应关系如下：

- 根 `wf/workflow.lgwf` 保持薄编排，只连接阶段。
- 阶段 `wf/<stage>/workflow.lgwf` 编排本阶段内部节点。
- 阶段内部存在孙级 workflow 时，阶段 `workflow.lgwf` 保持薄编排，只连接业务子流程；孙级 `workflow.lgwf` 编排本子流程内部节点。
- Prompt 和 spec 放在阶段私有 `agents/`。
- 确定性文件操作、校验和转换放在阶段私有 `scripts/`。
- 模板、schema、示例和确认文案放在阶段私有 `resources/`。
- 跨阶段 Python helper 可放在 `wf/shared/scripts/`。

共享 helper 只能承载稳定技术逻辑，不得承载阶段 prompt、approval prompt、业务 DSL 或阶段私有判断。

## 状态边界

运行状态与源码目录必须分离：

- workflow package 源码放在 `<package>/wf/`、`<package>/scripts/`、`<package>/tests/` 等目录。
- LGWF run state 只写入 `<package>/ws/.lgwf/`。
- facade 内部 workflow 的 work dir 以 `registry.json` 中的 `work_dir` 为准。
- 子 workflow 不拥有独立源码外状态目录；其运行产物仍通过当前 run 的 `.lgwf/` 或明确 artifact contract 管理。
- 目标 package 根目录不得写入 `.lgwf/`、`.tmp/`、`__pycache__/` 或临时运行文件。

父 workflow 不得直接依赖子 workflow `.lgwf` 内部临时文件。确需跨阶段或跨子流程消费时，应把结果固化为 confirmed artifact、report、handoff payload、父级 state 字段或 `artifact_contracts.json` 中声明的产物。

## 契约文件

顶层 workflow package 必须补齐以下契约：

- `AGENTS.md`：面向 agent 的入口、依赖、状态边界、产物、验证和禁止事项。
- `README.md`：面向维护者的定位、目录、阶段、验证和未覆盖范围。
- `entry_contract.json`：面向 facade/runner 的输入模式、schema、auto-human 策略、状态边界、输出和 resume 规则。
- `wf/artifact_contracts.json`：声明关键运行产物、确认后固化产物和报告。

子 workflow 和复杂 step 不一定都需要独立 JSON contract，但必须在本地文档或父级步骤设计中写清楚输入输出边界。孙级 workflow 必须至少有本地 `README.md` 或父级步骤设计条目说明职责、输入、输出、产物、验证和禁止事项。

## 路径规则

- 所有 resource path 必须使用包内相对路径。
- 禁止绝对路径、盘符路径、URL、`..` 和指向 `.lgwf` 的 resource path。
- 生成文件必须落在目标 package 内。
- `workflow.lgwf` 可以出现在 `wf/workflow.lgwf`、`wf/<stage>/workflow.lgwf` 和受控的 `wf/<stage>/<subflow>/workflow.lgwf`。第三层以上嵌套必须在父级步骤设计中说明必要性。
- Prompt、approval prompt、spec 和 stage-local resource 必须留在对应 `wf/<stage>/` 或 `wf/<stage>/<subflow>/` 目录内。

## 创建阶段要求

使用当前创建入口 `wf-create-fast` 创建 workflow 时，确认与落盘阶段应逐步收敛模块边界：

1. 需求确认：确认 workflow package 的用户意图、目标、非目标、输入、输出和风险边界。
2. 业务流确认：确认应拆成哪些阶段，哪些阶段需要人工确认、review、handoff 或独立验证。
3. scaffold 落盘：按已确认业务流生成并 materialize 目标 package 的最小目录、文件和状态边界。
4. 主 agent handoff：把已确认需求、业务流和已落盘 scaffold 交给主 agent，直接完善目标 package。

主 agent 后续实现必须显式遵守本文的目录、状态和验证边界；如果已落盘 scaffold 无法支撑需求，应在最终说明中列出保守假设和调整理由，不得静默改变模块边界。

## 验收清单

新增或调整 workflow 模块后，至少检查：

- 根目录没有多余可运行 `workflow.lgwf`。
- `wf/workflow.lgwf` 只做薄编排，阶段细节在 `wf/<stage>/`；如果存在孙级 workflow，父阶段 workflow 也只做子流程编排。
- 每个 `wf/<stage>/workflow.lgwf` 和 `wf/<stage>/<subflow>/workflow.lgwf` 都有明确业务职责、输入、输出和产物边界。
- 孙级 workflow 使用业务职责命名，不使用 `scripts`、`agents`、`resources` 等文件类型名称作为 workflow 边界。
- 每个 `wf/<stage>/` 或 `wf/<stage>/<subflow>/` 自包含阶段/子流程私有 prompt、script、resource。
- 共享目录没有阶段私有 prompt 或 approval prompt。
- `ws/.lgwf/` 是唯一运行状态目录。
- `AGENTS.md`、`README.md`、`entry_contract.json` 和 `artifact_contracts.json` 的边界描述一致。
- 资源路径不包含绝对路径、盘符、URL、`..` 或 `.lgwf`。
- 最小 audit/test 命令可执行，并写入对应入口文档。

## 与共享契约的关系

本文约束 workflow 创建和目录拆分方法。`workflows/01-share/module-contract.md` 约束模块入口文档必须声明的 Contract 字段。两者应同时使用：

- 先用本文决定 workflow、子 workflow、复杂 step 和目录边界。
- 再用 `module-contract.md` 补齐模块定位、入口、依赖、状态边界、产物、验证和禁止事项。

如果两份文档出现冲突，先保持更严格的状态隔离、路径限制和人工确认边界，再更新共享规范消除漂移。
