# LGWF Workflow Tools 场景路由表

显式指令由根目录 `SKILL.md` 直接路由。本文件只负责非显式指令的用户场景分流；具体规则、命令和执行细节写在 `docs/*.md` 中。

## 场景路由表

| 用户场景 | 下一步 |
| --- | --- |
| 询问可用命令、维护命令含义、发布保护或最小验证 | 读取 [docs/maintenance.md](docs/maintenance.md)。 |
| 询问目标 workflow 直启规则、路径解析或已有 run 处理方式 | 读取 [docs/target-run.md](docs/target-run.md)，启动后按需读取 [docs/facade-dispatch.md](docs/facade-dispatch.md)。 |
| 修复、创建、prompt 修复、prompt 升级、生成测试、复杂规划等普通 workflow 任务 | 读取 [docs/workflow-routing.md](docs/workflow-routing.md)。 |
| “修复优化”“完善”“整理”“质量提升”等范围不清且可能改文件的请求 | 先读取 [docs/proposal-gate.md](docs/proposal-gate.md)。 |
| self-improve、自我优化、复盘、沉淀 case、生成 proposal、生成 eval case | 读取 [docs/self-improve.md](docs/self-improve.md)。 |
| 启动、继续、监控、approval、`waiting_human`、run handle、收尾 | 读取 [docs/facade-dispatch.md](docs/facade-dispatch.md)。 |
| 准备内部 workflow 输入 JSON | 必要时查 [docs/workflow-inputs.md](docs/workflow-inputs.md)，最终以目标 workflow `AGENTS.md` 为准。 |

## 通用路由顺序

1. 确认请求不是 `SKILL.md` 已处理的显式指令。
2. 判断是否是 self-improve 或模糊修改请求。
3. 普通 workflow 任务交给 `docs/workflow-routing.md` 选择内部 workflow。
4. 每次派发内部 workflow 前读取 `registry.json` 和目标 workflow 的 `AGENTS.md`。
5. 需要真实运行或监控时，回到 `docs/facade-dispatch.md`。

## 输出要求

- 说明当前命中的用户场景。
- 说明读取了哪份场景引导文档。
- 如果选择内部 workflow，说明为什么选择目标 workflow。
