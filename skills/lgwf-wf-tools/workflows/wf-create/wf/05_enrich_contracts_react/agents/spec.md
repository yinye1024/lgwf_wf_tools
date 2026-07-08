# enrich_contracts_react 规格

## 职责

`enrich_contracts_react` 位于目标 workflow 初稿生成之后、最终 `validate_created_package` 之前。它负责根据运行态镜像 `.lgwf/create_reference_context/module-contract/module-contract.md` 给刚生成的目标 workflow package 补齐两类 Contract：入口文档中的模块自包含 Contract，以及目标 DSL 中所有节点的外部文件 I/O `CONTRACT`。它必须扫描目标 package 下所有 `workflow.lgwf`，为所有节点逐个生成或补齐 `CONTRACT`，并通过 observe 阶段运行 `lgwf.py audit`，直到目标 workflow 的 authoring audit 和 Contract 文档检查都通过。

## 稳定输入

- `.lgwf/implementation_context.json`：目标 package 的路径权威输入，包含 `target_package_abs` 和 `target_package_root`。
- `.lgwf/implementation_result.json`：实现阶段生成的文件与验证说明。
- `.lgwf/contract_observe.json`：上一轮 Contract observe 反馈；失败时下一轮必须优先修复其中的 `failures`。
- `.lgwf/create_reference_context/module-contract/module-contract.md`：由 `prepare_dsl_reference_context` 镜像而来的模块自包含契约，定义 `lgwf_workflow_package` 必须说明的定位、入口、依赖、状态边界、产物、验证和禁止事项。

## 写入范围

- 只允许修改 `target_package_abs` 指向的目标 package。
- 优先修改目标 package 的 `AGENTS.md` 和 `README.md`；只有这些文件不存在时才创建。
- 允许修改目标 package 内 `wf/workflow.lgwf` 和 `wf/<stage>/workflow.lgwf`，仅用于补齐节点级 `CONTRACT READ` / `CONTRACT WRITE`。
- 不得修改 `lgwf-wf-tools` facade、当前 `wf-create` 源码或运行目录 `.lgwf/`。
- 不得新增业务阶段、实现新功能、改写已确认步骤设计或替换 `workflow.lgwf` 的业务结构。

## Contract 要求

目标 package 的入口文档必须能让维护者不用追溯 `wf-create` run 就理解：

- 模块定位
- 入口
- 依赖
- 状态边界
- 产物
- 验证
- 禁止事项

如果目标 package 是 `lgwf_workflow_package`，说明必须覆盖 workflow root、work dir、最小 audit/test 命令、`.lgwf/` 状态边界、目标 package 产物和不得绕过 approval 的约束。

目标 package 的每个 DSL 节点也必须声明自己的节点外部文件 I/O：

- 扫描目标 package 下所有 `workflow.lgwf`，包括 `wf/workflow.lgwf` 和所有阶段子 workflow。
- 为所有节点逐个生成或补齐 `CONTRACT`；无外部业务文件 I/O 的节点可以没有 `CONTRACT`。
- `OUTPUT_JSON`、`OUTPUT_FILE` 和 `PERSIST` 必须有同节点 `CONTRACT WRITE workspace file`。
- 节点读取上游 `.lgwf/`、`reports/`、`data/` 等业务文件时，必须声明同节点 `CONTRACT READ workspace file`。
- 不要把节点内部临时文件、scratch 文件或 helper 缓存写入 `CONTRACT`。
- 不得把当前节点输出文件声明为同节点 `CONTRACT READ`。

## Observe 和退出

- observe 阶段运行确定性脚本，检查目标入口文档是否包含 Contract 必备段落，并执行 `lgwf.py audit <target>/wf/workflow.lgwf`；audit 负责校验 `OUTPUT_JSON`、`OUTPUT_FILE`、`PERSIST` 与同节点 `CONTRACT WRITE` 的一致性。
- `decide` 只在 `.lgwf/contract_observe.json` 的 `passed=true` 时退出。
- 如果 authoring audit 或 Contract 文档检查失败，下一轮只修复失败项，不扩大范围。
