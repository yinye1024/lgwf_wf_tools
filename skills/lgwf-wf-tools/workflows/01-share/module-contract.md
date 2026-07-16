# 模块自包含契约

本文件定义 `lgwf_wf_tools` 仓库内 skill 和 workflow 的统一模块边界。目标是让每个模块从自己的入口文档即可理解定位、入口、依赖、状态、产物、验证和禁止事项；自包含不表示复制 runtime 或 vendor，而是把运行和维护契约写清楚。

创建或调整 LGWF workflow 的目录边界、子 workflow 拆分、复杂 step 自包含和状态隔离时，先读取 facade 根目录 `docs/LGWF_WF_MODULAR_DEVELOPMENT.md`；本文负责在边界确定后补齐模块入口契约。

## 模块类型

- `codex_skill`：位于 `skills/<skill>/` 的 Codex skill package，必须有 `SKILL.md`、`AGENTS.md` 和 `README.md`。
- `lgwf_workflow_package`：通过 `workflow.lgwf` 由 LGWF runtime 执行的 workflow package，必须声明 workflow root、work dir 和最小 audit/test 方式。
- `tool_workflow`：由脚本或文档入口驱动、不走 LGWF runtime 的 workflow，必须声明 registry entry、执行入口和运行期产物目录。
- `entry_contract`：每个 registry workflow 的机器可读入口契约，声明输入模式、输入 schema、auto-human 策略、状态边界、输出和 resume 规则。

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
- `入口`：声明 registry id、`workflow_lgwf`、`work_dir`、`entry_contract.json` 和启动命令；普通 skill 内嵌 workflow 声明 `wf/workflow.lgwf`。
- `依赖`：声明 bundled client、共享规则、上下游 workflow 和目标 package 输入依赖。
- `状态边界`：运行状态只写入声明的 work dir 下 `.lgwf/`；workflow source root 与 work dir 必须分离。
- `产物`：列出主要 `.lgwf/` 文件、报告目录和 handoff payload。
- `验证`：提供 `lgwf.py audit` 和对应测试命令；只改文档时至少确认 UTF-8 和路径示例。
- `禁止事项`：资源路径必须相对，禁止绝对路径和 `..`；允许按模块化开发指引创建一层受控的阶段内部子 workflow，但该层不得继续嵌套更深的 `workflow.lgwf`，且必须声明职责、输入、输出和验证；不得绕过 approval。

## tool_workflow 契约

- `模块定位`：说明它是 registry 管理的内部 `tool_workflow`，不是 LGWF runtime workflow，也不是独立 Codex skill。
- `入口`：声明 `registry.json` 的 `id`、`kind`、`entry`、`agents_md`、`entry_contract.json`，以及脚本或文档入口。
- `依赖`：声明需要读取的共享规则、facade 文档、目标 workflow 或本地 manifest。
- `状态边界`：运行期记录、proposal、incident、scorecard 或 session 数据必须写入约定目录，不得混入发布包基线。
- `产物`：列出脚本输出、报告、proposal 或目标 package 生成物。
- `验证`：提供只读检查、manifest 校验或脚本 smoke test。
- `禁止事项`：不得要求 runtime audit，不得自动修改发布包、自动提交审批或绕过人工确认边界。

## self-improve 分层边界

- 已注册的内部 `lgwf_workflow_package` 应拥有自己的 `self-improve/` 模块，用于本 workflow 的 incident、proposal、eval、trace-eval、check 和 scorecard；运行期历史写入该 workflow 自己的 `.local/self-improve/`。
- 目标 workflow 的 `self-improve/` 必须自包含，不依赖 `lgwf-wf-tools/workflows/self-improve/` 的脚本；它可以使用当前 Python 环境中的 LGWF runtime 依赖，但不得调用 facade self-improve 代替本地检查。
- `lgwf-wf-tools/workflows/self-improve/` 只负责 facade 和跨模块治理，包括 registry 路由一致性、共享契约漂移、目标级 self-improve 覆盖率、发布前 gate 和跨模块 proposal；它不自动修改目标 workflow。
- `lgwf-wf-tools/workflows/self-improve-seed/` 只负责把通用 self-improve 结构安装到目标 workflow；默认不覆盖已有 `self-improve/`，不得删除目标 `.local/self-improve/` 历史。

## 维护要求

- 新增、转换、修复或优化任何 skill/workflow 时，先按 `docs/LGWF_WF_MODULAR_DEVELOPMENT.md` 确认 workflow、子 workflow、复杂 step 和目录边界，再确认模块类型，并按对应契约补齐入口文档和 `entry_contract.json`。
- `lgwf-wf-tools` 内部 workflow 必须由 `registry.json` 派发；`workflows/01-share/` 只保存共享规则，不注册为 workflow。
- 共享规则可以被引用，但每个模块仍必须在自己的 `AGENTS.md` 中写出自身的具体入口、依赖、状态边界和验证命令。
