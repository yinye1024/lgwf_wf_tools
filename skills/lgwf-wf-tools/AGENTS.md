# LGWF Workflow Tools 工作流路由表

显式指令由根目录 `SKILL.md` 做 bootstrap 分发。本文件只负责 workflow router：根据用户意图选择 `registry.json` 中的 `workflows/<id>`，再读取目标 workflow 的 `AGENTS.md`。

## 前置分流

以下场景不从 workflow 路由表选择 id：

| 用户场景 | 下一步 |
| --- | --- |
| 询问可用命令、维护命令含义、发布保护或最小验证 | 读取 [docs/maintenance.md](docs/maintenance.md)。 |
| “修复优化”“完善”“整理”“质量提升”等范围不清且可能改文件的请求 | 先读取 [docs/proposal-gate.md](docs/proposal-gate.md)，确认目标后再进入 workflow 路由表。 |
| 启动、继续、监控、approval、`waiting_human`、run handle、收尾 | 回到当前已选择 workflow 的 `AGENTS.md` 和 `workflows/01-share/` 共用规则。 |
| 准备内部 workflow 输入 JSON | 必要时查 [docs/workflow-inputs.md](docs/workflow-inputs.md)，最终以目标 workflow `AGENTS.md` 为准。 |

## Workflow 路由表

| 用户场景 | 选择 workflow |
| --- | --- |
| 目标是运行失败、卡住、产物不对、需要自动诊断修复 | 选择 `wf-fix`。 |
| 目标是从原始意图创建新的 LGWF workflow 初稿 | 选择 `wf-create`。 |
| 目标是把现有 prompt workflow 转换为 `wf-create` 可消费的创建输入包和转换报告 | 选择 `wf-convert`。 |
| 目标是 prompt 文件缺失、引用不清、输入输出契约不完整、上下文约束不足 | 选择 `wf-prompt-fix`。 |
| 目标是 prompt 质量升级、角色职责重塑、评估标准、失败模式、上下游协作质量 | 选择 `wf-prompt-upgrade`。 |
| 目标是生成或刷新 workflow 的端到端测试 | 选择 `e2e-test-generator`。 |
| 目标是对给定 workflow 做全面校验、升级、优化、生成并运行 E2E 门禁 | 选择 `wf-post-fix`。 |
| 目标是复杂任务规划、先产出计划/验收契约、用户确认后再执行 | 选择 `plan`。 |
| 用户显式要求目标 workflow 直启、路径解析或已有 run 处理方式 | 选择 `target-run`。 |
| 用户要求把 self-improve 能力加到目标 workflow、构造自包含自我提升结构、让目标 workflow 具备类似 self-improve 的自我进化能力 | 选择 `self-improve-seed`。 |
| self-improve、自我优化、复盘、沉淀 case、生成 proposal、生成 eval case、优化方案 | 选择 `self-improve`。 |

## 通用路由顺序

1. 确认请求不是 `SKILL.md` 已处理的维护指令。
2. 判断请求是否命中前置分流；命中时按前置分流处理，不读取 `registry.json`。
3. 未命中前置分流时，从 Workflow 路由表选择一个 workflow id。
4. 读取 `registry.json`，确认目标 workflow 的 `kind`、路径和 `agents_md`。
5. 读取目标 `workflows/<id>/AGENTS.md`。
6. 目标 `AGENTS.md` 再按需引用 `workflows/01-share/` 共用规则。

## 输出要求

- 说明当前命中的用户场景。
- 说明选择的 workflow id 和 `kind`。
- 说明读取了 `registry.json` 和哪个目标 `AGENTS.md`。
- 如果没有选择 workflow，说明读取了哪份 facade 文档。
