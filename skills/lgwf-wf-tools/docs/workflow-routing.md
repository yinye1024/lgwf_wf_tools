# 内部 Workflow 路由

本文用于普通 LGWF workflow 任务的内部 workflow 选择。实际路径、固定 `work_dir` 和 `agents_md` 以根目录 `registry.json` 为准。

## 路由前置

进入内部 workflow 路由前，先列出可用 workflow，优先运行：

```powershell
python scripts/list_workflows.py
```

随后读取 `registry.json` 和目标 workflow 的 `AGENTS.md`，并说明为什么选择目标 workflow。

## Workflow 选择表

| Workflow id | 使用时机 |
| --- | --- |
| `wf-fix` | 目标是运行失败、卡住、产物不对、需要自动诊断修复。 |
| `wf-create` | 目标是从原始意图创建新的 LGWF workflow 初稿；使用 `wf-create`。 |
| `wf-prompt-fix` | 目标是 prompt 文件缺失、引用不清、输入输出契约不完整、上下文约束不足。 |
| `wf-prompt-upgrade` | 目标是 prompt 质量升级、角色职责重塑、评估标准、失败模式、上下游协作质量。 |
| `e2e-test-generator` | 目标是生成或刷新 workflow 的端到端测试。 |
| `plan` | 目标是复杂任务规划、先产出计划/验收契约、用户确认后再按 ReAct 闭环执行。 |

## 证据修正

- 用户说“修复 workflow”，但证据只指向 prompt 基础规范且不需要真实运行目标 workflow：使用 `wf-prompt-fix`。
- 用户说“优化 prompt”，但目标 workflow 已经有明确运行失败证据：使用 `wf-fix`。
- 用户说“生成测试”，但目标 `workflow.lgwf` 不能解析或基础契约明显缺失：报告前置阻塞，并建议转入 `wf-fix` 或 `wf-prompt-fix`。
- 目标目录还没有可解析的 `workflow.lgwf`，且用户目标是创建新的 LGWF workflow：使用 `wf-create`。
- 用户要求交付质量治理：从 `wf-prompt-fix` 开始；阶段完成后，基于结果证据决定是否重新路由。

## 连续路由

每个阶段只选择一个内部 workflow。本 facade 不默认组装多个 workflow，不默认连续执行质量链路；阶段结果需要继续处理时，再重新列出候选、说明理由并重新路由。

## 输入和派发

准备 `--input-json` 时查 [workflow-inputs.md](workflow-inputs.md)，最终以目标 workflow `AGENTS.md` 为准。

启动、监控、approval 和收尾按 [facade-dispatch.md](facade-dispatch.md) 执行。
