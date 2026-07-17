# LGWF 与 lgwf-wf-tools 入门引导

本文是 `lgwf-guide` 的普通对话入口，用于帮助用户提出合适的问题，快速理解 LGWF 和 `lgwf-wf-tools`。本入口不启动 LGWF runtime，不创建运行状态，也不修改文件。

## 适用场景

- `/lgwf-wf-tools guide`
- `/lgwf-wf-tools learn`
- `/lgwf-wf-tools 入门`
- 只调用 `/lgwf-wf-tools`，入口预检通过且没有提供具体任务
- “怎么快速了解 LGWF？”
- “带我入门 LGWF。”
- “`lgwf-wf-tools` 能做什么、应该怎么用？”

如果用户已经明确要求创建、运行、修复、测试或优化 workflow，不进入本引导，直接回到 facade 根 `AGENTS.md` 路由。`/lgwf-wf-tools help` 和 `/lgwf-wf-tools 帮助` 只展示帮助，也不进入本引导。

## 默认开场

用户只有宽泛学习意图时，直接展示下面 7 个问题。前三题是优先核心问题，后四题用于进阶。允许用户回复序号、直接复制其中一个问题，或一次性复制后面的完整提示。

想快速了解 LGWF，建议按下面 7 个问题依次问，基本能覆盖“是什么、怎么写、怎么跑、怎么恢复”：

### 优先核心三问

1. **我为什么要用 LGWF，而不是继续使用现在的 prompt 工作流？LGWF 解决了哪些 prompt 工作流难以稳定处理的问题，什么情况下又没有必要迁移？**
2. **请用仓库中一个最小 workflow，演示从输入、节点执行到产物输出的完整过程。**
3. **`workflow.lgwf` 的核心语法有哪些？节点、依赖、条件分支和子 workflow 怎么表达？**

### 进阶四问

4. **LGWF 如何保存运行状态？`work_dir`、run、节点结果和产物之间是什么关系？**
5. **`approval`、`review`、`human_choice`、`waiting_human` 分别在什么场景使用？**
6. **workflow 失败或中断后，如何查看状态、定位问题、重试和继续执行？**
7. **LGWF 引擎、`lgwf-client-assist`、`lgwf-wf-tools`、registry 和 workflow package 分别负责什么？**

一次性提问模板：

> 请基于当前仓库，用一个真实且最小的 workflow 帮我快速理解 LGWF。先说明我为什么不继续使用现有 prompt 工作流：LGWF 增加了哪些能力、引入了哪些成本、什么情况下不值得迁移。再依次说明核心 DSL、输入输出、执行过程、状态保存、人工确认、失败恢复，以及它与 `lgwf-wf-tools` 的关系。尽量引用具体文件，并在最后给出一个可运行的最小示例和学习路线。

如果只问三题，优先问第 **1、2、3** 题；它们分别回答“有没有必要从 prompt 工作流迁移”“LGWF 实际怎样运行”“怎样阅读和编写”。需要开始实际操作和排障时，再继续第 **4、5、6、7** 题。

只有裸 `/lgwf-wf-tools` 入口已经实际完成 doctor 预检时，才在上述内容前增加“预检已通过”。其他触发方式不展示未经执行的预检结论。

## 补充提问路径

### 运行现有 Workflow

1. 运行一个 workflow 前必须准备哪些路径和输入？
2. `workflow.lgwf` 与 `work_dir` 为什么必须分开？
3. 如何查看运行状态、日志、产物和待处理的人工确认？
4. `continue`、`resume` 和 `rerun` 分别适合什么情况？
5. 如何通过 `lgwf-wf-tools` 直启一个目标 workflow？

### 阅读或创建 Workflow

1. `workflow.lgwf` 的核心声明和节点类型有哪些？
2. 普通 step、子 workflow、prompt、script 和 resource 应该如何划分目录？
3. 输入、输出、state 和 artifact contract 如何连接？
4. 哪些场景需要 approval、review、choice 或 handoff？
5. 创建后如何进行 audit、测试和最小运行验证？

### 排查运行问题

1. workflow 失败时应该先收集哪些状态、日志和 run record？
2. 如何判断问题属于环境、DSL、prompt、runtime 还是业务逻辑？
3. workflow 卡在 `waiting_human` 或人工确认时应该检查什么？
4. 修复后应该 `resume` 还是 `rerun`？
5. `wf-fix`、`wf-audit-fix` 和 `wf-post-fix` 的职责有什么区别？

### 使用 lgwf-wf-tools

1. `lgwf-wf-tools` 为什么是 facade，它与 bundled `lgwf-client-assist` 是什么关系？
2. `SKILL.md`、根 `AGENTS.md`、`registry.json` 和 `entry_contract.json` 如何共同完成路由？
3. 当前 registry 中有哪些 workflow，各自解决什么问题？
4. `doctor`、`list`、`guide` 和 `run` 分别什么时候使用？
5. 我当前的目标应该路由到哪个模块，为什么？

## 回答规则

- 用户提出具体问题时直接回答，不先重复完整问题清单。
- 回答保持短而完整：先给结论，再给一个当前仓库中的文件、命令或 workflow 示例。
- 涉及当前能力、路径和命令时读取当前仓库事实源，不依赖静态记忆。
- 每次回答结尾最多推荐一个下一问题；用户表示只需要概览时，不继续追问。
- 用户明确要求执行具体任务时，说明将退出引导并交回 facade 路由；本模块自身不启动任何 workflow。

## 事实源路由

- LGWF 使用和运行：`vendor/lgwf-client-assist/references/workflow-usage.md`。
- DSL 和 workflow 目录：`vendor/lgwf-client-assist/references/dsl-assist/guide.md`，按需继续读取它指向的文档。
- runtime 排障：`vendor/lgwf-client-assist/references/runtime-assist/guide.md`。
- `lgwf-wf-tools` 定位和入口：根 `README.md`、`SKILL.md` 和 `AGENTS.md`。
- 当前可用模块：`registry.json` 及目标 workflow 的 `entry_contract.json`、`AGENTS.md`。

## 后续路由

引导本身不执行后续任务。用户明确提出行动请求后，回到根 `AGENTS.md`，常见对应关系如下：

- 运行指定 workflow：`target-run`。
- 创建新 workflow：`wf-create-fast`。
- 诊断并修复运行问题：`wf-fix`。
- 修复静态 DSL audit 问题：`wf-audit-fix`。
- 全面校验和升级现有 workflow：`wf-post-fix`。
- 查看、复盘和改进 facade：`self-improve`。
