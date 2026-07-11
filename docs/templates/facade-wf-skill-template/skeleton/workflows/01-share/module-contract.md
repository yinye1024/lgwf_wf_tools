# 模块自包含契约

本文定义 facade workflow skill 的统一模块边界。目标是让每个模块从自己的入口文档即可理解定位、入口、依赖、状态、产物、验证和禁止事项。

## 模块类型

- `codex_skill`：对外 Codex skill package，必须有 `SKILL.md`、`AGENTS.md` 和 `README.md`。
- `lgwf_workflow_package`：通过 `workflow.lgwf` 由 LGWF runtime 执行的 workflow package，必须声明 workflow root、work dir 和最小验证方式。
- `tool_workflow`：由脚本或文档入口驱动、不走 LGWF runtime 的 workflow，必须声明 registry entry、执行入口和运行期产物目录。
- `entry_contract`：每个 registry workflow 的机器可读入口契约，声明输入模式、输入 schema、auto-human 策略、状态边界、输出和 resume 规则。

## codex_skill 契约

- `模块定位`：说明 skill 面向的用户意图、职责边界，以及是否只是 facade。
- `入口`：声明 `SKILL.md` 触发方式、主要命令和脚本入口。
- `依赖`：声明 runtime、registry、其他 skill 或外部仓库依赖。
- `状态边界`：声明运行状态写入位置。
- `产物`：列出主要输出文件、报告或 session manifest。
- `验证`：提供最小可执行验证命令。
- `禁止事项`：声明不能绕过 facade、不能写错状态目录或不能自动审批。

## lgwf_workflow_package 契约

- `模块定位`：说明该 workflow 是 facade 内部 workflow，不是独立 Codex skill。
- `入口`：声明 registry id、`workflow_lgwf`、`work_dir`、`entry_contract.json` 和启动命令。
- `依赖`：声明 runtime、共享规则、上下游 workflow 和目标输入依赖。
- `状态边界`：运行状态只写入声明的 work dir 下 `.lgwf/`。
- `产物`：列出主要 `.lgwf/` 文件、报告目录和 handoff payload。
- `验证`：提供 audit、脚本测试或最小 smoke test。
- `禁止事项`：禁止绝对资源路径，禁止绕过 approval，禁止把 work dir 放进源码目录。

## tool_workflow 契约

- `模块定位`：说明它是 registry 管理的内部 `tool_workflow`。
- `入口`：声明 registry id、`kind`、`entry`、`agents_md` 和 `entry_contract.json`。
- `依赖`：声明需要读取的共享规则、facade 文档或目标 package。
- `状态边界`：运行期记录、proposal、incident、scorecard 或 session 数据必须写入约定目录。
- `产物`：列出脚本输出、报告、proposal 或目标 package 生成物。
- `验证`：提供只读检查、manifest 校验或脚本 smoke test。
- `禁止事项`：不得要求 runtime audit，不得自动提交审批或绕过人工确认边界。

## 维护要求

新增、转换、修复或优化任何 skill/workflow 时，先确认模块类型，再补齐入口文档和 `entry_contract.json`。
