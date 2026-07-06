# LGWF Workflow Tools 工作流路由表

## 模块类型

- `codex_skill`
- facade skill，内部 `lgwf_workflow_package` 和 `tool_workflow` 由 `registry.json` 管理

## 模块定位

显式指令由根目录 `SKILL.md` 做 bootstrap 分发。本文件只负责 workflow router：根据用户意图选择 `registry.json` 中的 `workflows/<id>`，再读取目标 workflow 的 `entry_contract.json` 和 `AGENTS.md`。

创建、转换、修复或优化任何 skill/workflow 模块时，必须读取 `workflows/01-share/module-contract.md`，先确认模块类型，再补齐入口、依赖、状态边界、产物、验证和禁止事项。

## 入口

- Codex 入口：`SKILL.md`。
- 路由入口：本文件、`registry.json` 和每个 workflow 的 `entry_contract.json`。
- 维护入口：`docs/maintenance.md`。
- 内部 LGWF workflow 启动入口：`scripts/run_skill_workflow.py --workflow-id <id>`，由代理脚本按 `entry_contract.json` 自动补 runtime 参数和输入文件。

## 依赖

- 依赖内置 `vendor/lgwf-client-assist/` 执行 LGWF workflow。
- 依赖 `workflows/01-share/` 提供共享规则。

## 状态边界

- facade 本地状态写入 `.local/`。
- LGWF workflow 状态写入 registry 声明的 `work_dir/.lgwf/`。
- `tool_workflow` 按自身 `AGENTS.md` 声明写入 `.local/`、目标 package 或约定输出目录。

## 产物

- workflow run records、approval 展示、proposal、报告和 handoff payload 按目标 workflow 约定写入。

## 验证

```powershell
python skills\lgwf-wf-tools\scripts\doctor_lgwf_wf_tools.py
python skills\lgwf-wf-tools\scripts\doctor_lgwf_wf_tools.py --deep
python -m unittest discover skills\lgwf-wf-tools\tests
```

## 前置分流

以下场景不从 workflow 路由表选择 id：

| 用户场景 | 下一步 |
| --- | --- |
| 询问可用命令、维护命令含义、发布保护或最小验证 | 读取 [docs/maintenance.md](docs/maintenance.md)。 |
| “修复优化”“完善”“整理”“质量提升”等范围不清且可能改文件的请求 | 先读取 [docs/proposal-gate.md](docs/proposal-gate.md)，确认目标后再进入 workflow 路由表。 |
| 启动、继续、监控、approval、`waiting_human`、run handle、收尾 | 回到当前已选择 workflow 的 `AGENTS.md` 和 `workflows/01-share/` 共用规则。 |
| 准备内部 workflow 输入 JSON | 先读取 registry 指向的 `entry_contract.json`，必要时查 [docs/workflow-inputs.md](docs/workflow-inputs.md)，再参考目标 workflow `AGENTS.md`。 |

## Workflow 路由表

| 用户场景 | 选择 workflow |
| --- | --- |
| 目标是运行失败、卡住、产物不对、需要自动诊断修复 | 选择 `wf-fix`。 |
| 目标是从原始意图创建新的 LGWF workflow 初稿 | 选择 `wf-create`。 |
| 目标是把现有 prompt workflow 转换为 `wf-create` 可消费的创建输入包和转换报告 | 选择 `wf-convert`。 |
| 目标是 prompt 文件缺失、引用不清、输入输出契约不完整、上下文约束不足 | 选择 `wf-prompt-fix`。 |
| 目标是 prompt 质量升级、角色职责重塑、评估标准、失败模式、上下游协作质量 | 选择 `wf-prompt-upgrade`。 |
| 目标是 LGWF 升级后批量处理旧 workflow 的 DSL 兼容性、语法迁移、静态 audit 诊断和受控升级 | 选择 `wf-dsl-upgrade`。 |
| 目标是生成或刷新 workflow 的端到端测试 | 选择 `e2e-test-generator`。 |
| 目标是对给定 workflow 做全面校验、升级、优化、生成并运行 E2E 门禁 | 选择 `wf-post-fix`。 |
| 目标是复杂任务规划、先产出计划/验收契约、用户确认后再执行 | 选择 `plan`。 |
| 目标是把带 `wf/workflow.lgwf` 的 Codex skill 打包成内置 `lgwf-client-assist` runtime 的自包含 skill | 选择 `skill-packaging`。 |
| 用户显式要求目标 workflow 直启、路径解析或已有 run 处理方式 | 选择 `target-run`。 |
| 用户要求把 self-improve 能力加到目标 workflow、构造自包含自我提升结构、让目标 workflow 具备类似 self-improve 的自我进化能力 | 选择 `self-improve-seed`。 |
| self-improve、自我优化、复盘、沉淀 case、生成 proposal、生成 eval case、优化方案 | 选择 `self-improve`。 |

## 通用路由顺序

1. 确认请求不是 `SKILL.md` 已处理的维护指令。
2. 判断请求是否命中前置分流；命中时按前置分流处理，不读取 `registry.json`。
3. 未命中前置分流时，从 Workflow 路由表选择一个 workflow id。
4. 读取 `registry.json`，确认目标 workflow 的 `kind`、路径、`entry_contract` 和 `agents_md`。
5. 读取目标 `entry_contract.json`，确认输入模式、required fields、state boundary 和 `auto_human_policy`。
6. 读取目标 `workflows/<id>/AGENTS.md`。
7. 对 `kind=lgwf` 的内部 workflow，优先通过 `scripts/run_skill_workflow.py --workflow-id <id>` 启动；只有底层排障时才直接调用 vendor `lgwf.py run`。
8. 目标 `AGENTS.md` 再按需引用 `workflows/01-share/` 共用规则。

## `wf-create` 执行纪律

命中 `wf-create` 后必须启动或继续同一个 `wf-create` run，不能由主 agent 直接手工创建目标 workflow package、直接写目标 `workflow.lgwf`、直接注册 registry，或把创建流程替换为 `apply_patch` 脚手架。

只有在已经启动或继续 `wf-create`、且 runtime/子 Codex 进程出现可复核异常时，才允许进入异常恢复。异常恢复前必须先向用户展示 run id、状态文件或进程证据、已产物、未完成阶段和可选方案；用户明确确认后，才可以做人工恢复或转入其他 workflow。

## 输出要求

- 说明当前命中的用户场景。
- 说明选择的 workflow id 和 `kind`。
- 说明读取了 `registry.json`、哪个 `entry_contract.json` 和哪个目标 `AGENTS.md`。
- 如果没有选择 workflow，说明读取了哪份 facade 文档。

## 禁止事项

- 不要把内部 workflow 注册为独立 Codex skill。
- 不要绕过 `workflows/01-share/approval.md` 的人工确认展示模板。
- 不要在 registry 中保留不存在的 workflow entry。
- 不要再把静态 audit 修复请求路由到本 facade；这类请求应使用独立 `wf-audit-fix` skill。
