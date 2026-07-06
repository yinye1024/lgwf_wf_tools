# 内部 Workflow 路由

本文用于普通 LGWF workflow 任务的内部 workflow 选择。实际路径、固定 `work_dir` 和 `agents_md` 以根目录 `registry.json` 为准。

## 路由前置

进入内部 workflow 路由前，先列出可用 workflow，优先运行：

```powershell
python scripts/list_workflows.py
```

随后读取 `registry.json`、目标 workflow 的 `entry_contract.json` 和目标 workflow 的 `AGENTS.md`，并说明为什么选择目标 workflow。

## Workflow 选择表

| Workflow id | 使用时机 |
| --- | --- |
| `wf-fix` | 目标是运行失败、卡住、产物不对、需要自动诊断修复。 |
| `wf-create` | 目标是从原始意图创建新的 LGWF workflow 初稿；使用 `wf-create`。 |
| `wf-convert` | 目标是把现有 prompt workflow 转换为 `wf-create` 可消费的创建输入包和转换报告。 |
| `wf-prompt-fix` | 目标是 prompt 文件缺失、引用不清、输入输出契约不完整、上下文约束不足。 |
| `wf-prompt-upgrade` | 目标是 prompt 质量升级、角色职责重塑、评估标准、失败模式、上下游协作质量。 |
| `e2e-test-generator` | 目标是生成或刷新 workflow 的端到端测试。 |
| `plan` | 目标是复杂任务规划、先产出计划/验收契约、用户确认后再按 ReAct 闭环执行。 |

## 证据修正

- 用户说“修复 workflow”，但证据只指向 prompt 基础规范且不需要真实运行目标 workflow：使用 `wf-prompt-fix`。
- 用户说“修复 workflow audit”或只要求修复 DSL / audit 静态问题，且明确不需要运行目标 workflow：不从本 facade registry 路由，改用独立 `wf-audit-fix` skill。
- 用户说“优化 prompt”，但目标 workflow 已经有明确运行失败证据：使用 `wf-fix`。
- 用户说“生成测试”，但目标 `workflow.lgwf` 不能解析或基础契约明显缺失：报告前置阻塞，并建议转入 `wf-fix` 或 `wf-prompt-fix`。
- 目标目录还没有可解析的 `workflow.lgwf`，且用户目标是创建新的 LGWF workflow：使用 `wf-create`。
- 目标目录是 prompt workflow 或主要由 prompt/Markdown/JSON/YAML 文件组成，且用户目标是先生成 `wf-create` 输入包：使用 `wf-convert`。
- 用户要求交付质量治理：从 `wf-prompt-fix` 开始；阶段完成后，基于结果证据决定是否重新路由。

## 连续路由

每个阶段只选择一个内部 workflow。本 facade 不默认组装多个 workflow，不默认连续执行质量链路；阶段结果需要继续处理时，再重新列出候选、说明理由并重新路由。

## 输入和派发

准备输入时先读 registry 指向的 `entry_contract.json`，必要时查 [workflow-inputs.md](workflow-inputs.md)，业务纪律以目标 workflow `AGENTS.md` 为准。内部 workflow 推荐通过代理脚本按 workflow id 启动：

```powershell
python scripts\run_skill_workflow.py --workflow-id <id> --input-json-file <utf8-json-file> --background
```

代理脚本会按 contract 自动补 `--workflow-lgwf`、`--work-dir`，并在需要时把 `--input-json` 转为 UTF-8 no BOM `--input-json-file`。`input_mode=input_json_required` 的 workflow 必须显式提供 `--input-json-file` 或 `--input-json`；`empty_then_approval` 和 `no_input` 会自动使用 contract 示例，通常是 `{}`。

只有用户显式要求 `--auto-human`，且目标 contract 的 `auto_human_policy` 不是 `forbidden` 时，代理脚本才会向 runtime 透传 `--auto-human`。`conditional` 表示调用者已经确认目标范围明确授权；`forbidden` 会直接拒绝启动。

启动、监控、approval 和收尾按 [facade-dispatch.md](facade-dispatch.md) 执行。

## `wf-create` 启动约束

命中 `wf-create` 后，主 agent 必须启动或继续 `wf-create` run，并按 `workflows/wf-create/AGENTS.md` 处理 approval、resume、monitor 和 handoff。

禁止主 agent 直接手工创建目标 workflow package、直接写目标 DSL 或 registry entry，或用 `apply_patch` 脚手架替代 `wf-create` 的确认阶段。只有在 `wf-create` 已启动或继续后出现可复核的 runtime/子进程异常，且用户基于证据明确确认恢复方案时，才允许人工恢复。
