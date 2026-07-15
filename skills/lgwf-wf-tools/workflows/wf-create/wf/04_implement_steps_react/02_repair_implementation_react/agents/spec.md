# repair_implementation_react 规格

## 职责

`repair_implementation_react` 只负责根据 Python audit 反馈修复 `01_implement_units` 已生成的初版 workflow package。它不负责首版设计解释，不重新拆解 `.lgwf/step_designs.json`，也不扩展已确认范围。

## 稳定输入边界

- Python OBSERVE 使用 `.lgwf/step_designs.json`、`.lgwf/implementation_context.json` 和 `.lgwf/implementation_result.json` 执行确定性检查。
- Python OBSERVE 只把已确认 step/file/directory 设计和 `package_profile` 作为结构校验事实，不把它们交给 REASON 做语义扩展。
- `.lgwf/implementation_audit_result.json` 是 REASON 的确定性 audit 事实源。
- `.lgwf/implementation_observe.json` 是 REASON 的确定性 audit 反馈。
- `.lgwf/implementation_decision.json` 和 `.lgwf/implementation_repair_decision_analysis.json` 是 REASON 的小体量路由反馈。
- `.lgwf/implementation_repair_reason.json` 是 reason slot 写给 act slot 的唯一修复计划。

## ReAct 共同准则

- REASON 只能把 `.lgwf/implementation_audit_result.json` 和 `.lgwf/implementation_observe.json` 中的 Python 检查失败转成最小 repair plan。
- ACT 只能修改 repair plan 指定的 package-relative files，不能重新生成全包。
- OBSERVE 由 Python audit 执行，必须保留脚本 audit 的失败证据，不得把脚本 audit 的失败结果改写为通过。
- DECIDE 由 Python 脚本根据 audit/observe 结果写入 `next`。
- 修复计划以 Python audit 暴露的失败项为边界；未进入 audit/observe 的问题留给后续人工或专门流程。
- 修复阶段不得写 `.lgwf/step_designs.json`，不得修改已确认步骤设计，不得读取 reference、`03_confirm_step_designs` 的 prompt 或 tests 反推设计。
- `workflow.lgwf` 只能生成在 `wf/workflow.lgwf` 或 `wf/<stage>/workflow.lgwf`；不得生成 `wf/<stage>/<substage>/workflow.lgwf`。
- DSL 节点不得使用裸 `INPUT state.*` 绕过文件/上下文契约。

## 路径与写入边界

- `target_package_abs` 只供发布脚本和 audit 使用；Codex ACT 只能写 `.lgwf/implementation_repair_stage/<target_file>` 对应的 staging 文件。
- `target_package_root` 是 `workspace_root` 相对路径，不是当前运行目录 `work_dir` 相对路径。
- 禁止从 `work_dir` 使用 `..`、固定层级上跳或拼接仓库根路径。
- 所有修复文件必须是目标 package 内相对路径，不得使用绝对路径、盘符路径、URL、`.lgwf` 或 `..`。
- 修复阶段不负责 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成、自动运行保证或端到端业务成功。
