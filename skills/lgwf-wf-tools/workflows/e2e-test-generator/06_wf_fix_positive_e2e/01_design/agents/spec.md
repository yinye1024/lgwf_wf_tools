# wf-fix 正向 E2E 质量规范

wf-fix 正向 E2E 的职责是复用真实 Codex 正向场景，启动 `wf-fix` 对原始目标 `workflow.lgwf` 执行边跑边修复闭环。它是人工显式入口，不属于回归测试集。

必须满足：

- 使用 `wf-fix`，启动入口为 `skills/lgwf-wf-tools/workflows/wf-fix/wf/workflow.lgwf`。
- 目标仍是原始 `target_workflow_lgwf`，不得把生成的 Python 脚本当成目标 workflow。
- 启动 `wf-fix` 前必须执行或封装 `lgwf.py audit <target workflow.lgwf>`，audit 目标是原始目标 `workflow.lgwf`；不得 audit Python 脚本，也不得 audit `wf-fix` 自身。
- 复用或对齐 `.lgwf/e2e_real_positive_design.json` 的业务输入、fixture、approval 决策和黑盒断言。
- 自修复请求固定包含 `max_attempts=5` 和 `ask_main_agent_for_target_approvals=true`。
- 自动提交目标 workflow input-json，并自动处理 approval。
- 最终检查 `self_fix_summary`、最后一轮目标 run 成功证据和业务黑盒结果。
- audit 失败、wf-fix 失败或超时时，保留 audit 输出、wf-fix work dir、目标 run artifact、输入 JSON、summary 和业务 fixture。

禁止：

- 被 `unittest discover` 或常规回归入口自动运行。
- 使用环境变量作为是否运行 `wf-fix` 的门禁。
- 在生成器验收阶段真实启动 `wf-fix`。
