# repair_implementation_react 规格

## 职责

`repair_implementation_react` 只负责优化和修复 `01_implement_units` 已生成的初版 workflow package。它不负责首版设计解释，不重新拆解 `.lgwf/step_designs.json`，也不扩展已确认范围。

## 稳定输入

- `.lgwf/step_designs.json` 是唯一设计契约。
- `.lgwf/step_designs.json` 的结构化输入契约以已确认 `confirmed` 内容为准，修复阶段只消费结构化 `step_designs[]` 条目，不重新设计。
- `.lgwf/scaffold_package_result.json` 中的 `scaffold_plan` 是目录、文件和阶段 manifest 的结构事实源。
- `scaffold_plan.package_profile` / `package_profile` 是目标 package 类型约束，修复时只能维持该 profile 下已确认的结构。
- `.lgwf/implementation_context.json` 是路径权威输入，包含 `workspace_root`、`target_package_root`、`target_package_abs` 和 `work_dir`。
- `.lgwf/implementation_result.json` 是初版实现或上一轮修复后的实现结果。
- `.lgwf/implementation_audit_result.json` 是确定性 audit 事实源。
- `.lgwf/implementation_observe.json` 是 observe slot 对 audit 事实的语义归纳。
- `.lgwf/implementation_repair_reason.json` 是 reason slot 写给 act slot 的唯一修复计划。
- `.lgwf/create_reference_context/implementation-reference-index.md` 是 DSL、audit 和模块化参考入口。

## ReAct 共同准则

- REASON 只能把 observe/audit 反馈转成最小 repair plan。
- ACT 只能修改 repair plan 指定的 package-relative files，不能重新生成全包。
- OBSERVE 必须保留脚本 audit 的失败证据，不得把脚本 audit 的失败结果改写为通过。
- DECIDE 可以分析是否继续，但最终 `next` 只能由 Python 脚本写入。
- 修复阶段不得写 `.lgwf/step_designs.json`，不得修改 scaffold plan，不得读取 `03_confirm_step_designs` 的 prompt 或 tests 反推设计。
- `workflow.lgwf` 只能生成在 `wf/workflow.lgwf` 或 `wf/<stage>/workflow.lgwf`；不得生成 `wf/<stage>/<substage>/workflow.lgwf`。
- DSL 节点不得使用裸 `INPUT state.*` 绕过文件/上下文契约。

## 路径与写入边界

- `target_package_abs` 只供发布脚本和 audit 使用；Codex ACT 只能写 `.lgwf/implementation_repair_stage` 下的 `workspace_output_files`。
- `target_package_root` 是 `workspace_root` 相对路径，不是当前运行目录 `work_dir` 相对路径。
- 禁止从 `work_dir` 使用 `..`、固定层级上跳或拼接仓库根路径。
- 所有修复文件必须是目标 package 内相对路径，不得使用绝对路径、盘符路径、URL、`.lgwf` 或 `..`。
- 修复阶段不负责 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成、自动运行保证或端到端业务成功。
