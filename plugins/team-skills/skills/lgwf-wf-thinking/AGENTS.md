# lgwf-wf-thinking 协作指引

## 定位

`lgwf-wf-thinking` 是独立 Codex skill package，不是 `lgwf-wf-tools` 的内部 workflow package。它必须保留根 `SKILL.md`、`AGENTS.md`、`agents/openai.yaml`，并在内部携带可运行的 `wf/workflow.lgwf` 与 `ws/.gitkeep`。

本 skill 的职责是先思考和编排，不直接替代执行器：

- 根据用户需求识别是创建、修复、转换、优化、测试生成、提示词改进还是治理类工作。
- 读取当前可用 workflow 能力，形成组合方案。
- 通过 `confirm_plan` 让用户确认或微调方案。
- 输出可交给 `lgwf-wf-tools` 的 handoff 指令包。

## 必须遵守

- 默认用中文编写面向人的说明、报告、prompt 和验收信息。
- 新增或修改中文文本文件时使用 UTF-8。
- 运行前必须读取当前可用 workflow registry，优先路径为 `../lgwf-wf-tools/registry.json`。
- 不要使用 `internal_workflow_package` 规则；不要因为内置了 `wf/workflow.lgwf` 就省略根 `SKILL.md`。
- 不要在 `lgwf-wf-thinking` 中直接执行下游 workflow。实际执行必须由用户确认后交给 `lgwf-wf-tools`。
- 不要绕过 `lgwf-wf-tools` 的审批代理、监控、resume/rerun 和 run handle 规则。

## 推荐流程

1. 收集用户的 workflow 需求和上下文边界。
2. 读取 `lgwf-wf-tools` registry，列出候选 workflow。
3. 分类需求，标注主任务、辅助任务、风险和缺口。
4. 用 `compose_plan` ReAct 循环生成组合方案。
5. 用 `confirm_plan` 收集用户确认或微调意见。
6. 生成 handoff 指令包，明确要由 `lgwf-wf-tools` 运行哪些 workflow、顺序、输入和验收标准。

## 验证

最小验证命令：

```powershell
python plugins/team-skills/skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py audit plugins/team-skills/skills/lgwf-wf-thinking/wf/workflow.lgwf
```

