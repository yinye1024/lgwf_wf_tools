# 模块自包含契约

本文件定义 `lgwf_wf_tools` 仓库内 skill 和 workflow 的统一模块边界。目标是让每个模块从自己的入口文档即可理解定位、入口、依赖、状态、产物、验证和禁止事项；自包含不表示复制 runtime 或 vendor，而是把运行和维护契约写清楚。

## 模块类型

- `codex_skill`：位于 `skills/<skill>/` 的 Codex skill package，必须有 `SKILL.md`、`AGENTS.md` 和 `README.md`。
- `lgwf_workflow_package`：通过 `workflow.lgwf` 由 LGWF runtime 执行的 workflow package，必须声明 workflow root、work dir 和最小 audit/test 方式。
- `tool_workflow`：由脚本或文档入口驱动、不走 LGWF runtime 的 workflow，必须声明 registry entry、执行入口和运行期产物目录。

## codex_skill 契约

- `模块定位`：说明该 skill 面向的用户意图、职责边界，以及是否只是 facade、runner 或带自有 workflow 的 skill。
- `入口`：声明 `SKILL.md` 的触发方式、主要命令、脚本入口或自带 `wf/workflow.lgwf`。
- `依赖`：声明是否依赖 `lgwf-wf-tools/registry.json`、facade bundled client、其他 skill 或外部仓库。
- `状态边界`：声明运行状态写入位置；带 workflow 的 skill 应使用同级 `ws/`，脚本型 skill 应声明自己的 session 或 `.local/` 目录。
- `产物`：列出主要输出文件、报告或 session manifest。
- `验证`：提供最小可执行验证命令。
- `禁止事项`：声明不能绕过 facade、不能写错状态目录、不能自动审批或不能执行高风险写操作等边界。

## lgwf_workflow_package 契约

- `模块定位`：说明该 workflow 是否是 facade 内部 workflow、普通 skill 内嵌 workflow，且不得误注册为独立 Codex skill。
- `入口`：声明 registry id、`workflow_lgwf`、`work_dir` 和启动命令；普通 skill 内嵌 workflow 声明 `wf/workflow.lgwf`。
- `依赖`：声明 bundled client、共享规则、上下游 workflow 和目标 package 输入依赖。
- `状态边界`：运行状态只写入声明的 work dir 下 `.lgwf/`；workflow source root 与 work dir 必须分离。
- `产物`：列出主要 `.lgwf/` 文件、报告目录和 handoff payload。
- `验证`：提供 `lgwf.py audit` 和对应测试命令；只改文档时至少确认 UTF-8 和路径示例。
- `禁止事项`：资源路径必须相对，禁止绝对路径和 `..`；不得在子 workflow 下继续创建孙级 `workflow.lgwf`，不得绕过 approval。

## tool_workflow 契约

- `模块定位`：说明它是 registry 管理的内部 `tool_workflow`，不是 LGWF runtime workflow，也不是独立 Codex skill。
- `入口`：声明 `registry.json` 的 `id`、`kind`、`entry` 和 `agents_md`，以及脚本或文档入口。
- `依赖`：声明需要读取的共享规则、facade 文档、目标 workflow 或本地 manifest。
- `状态边界`：运行期记录、proposal、incident、scorecard 或 session 数据必须写入约定目录，不得混入发布包基线。
- `产物`：列出脚本输出、报告、proposal 或目标 package 生成物。
- `验证`：提供只读检查、manifest 校验或脚本 smoke test。
- `禁止事项`：不得要求 runtime audit，不得自动修改发布包、自动提交审批或绕过人工确认边界。

## 维护要求

- 新增、转换、修复或优化任何 skill/workflow 时，先确认模块类型，再按对应契约补齐入口文档。
- `lgwf-wf-tools` 内部 workflow 必须由 `registry.json` 派发；`workflows/01-share/` 只保存共享规则，不注册为 workflow。
- 共享规则可以被引用，但每个模块仍必须在自己的 `AGENTS.md` 中写出自身的具体入口、依赖、状态边界和验证命令。
