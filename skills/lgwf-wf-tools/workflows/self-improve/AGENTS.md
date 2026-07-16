# Self Improve Workflow

本目录是 `lgwf-wf-tools` facade 下的内部 `tool-workflow`，职责是对 facade 和已注册内部 workflow 做跨模块治理：registry 路由一致性、共享契约漂移、目标级 self-improve 覆盖率、真实问题沉淀、proposal 生成、eval case 草稿和发布前检查。它不是 LGWF runtime workflow，不包含 `workflow.lgwf`，不得作为独立 Codex skill 注册。

目标 workflow 自己的改进闭环必须由目标目录下的 `self-improve/` 负责；本 workflow 可以报告缺失、汇总 health 或生成跨模块 proposal，但不替代目标模块的局部 self-improve，也不自动修改目标 workflow。

## 共用规则

执行本 workflow 前必须读取：

- `../01-share/AGENTS.md`
- `../01-share/module-contract.md`
- `../01-share/registry-contract.md`
- `../01-share/tool-workflow.md`
- `../01-share/artifacts.md`

模块类型：`tool_workflow`。本模块的入口、依赖、状态边界、产物、验证和禁止事项以本文件后续章节为准。

入口参数、输入示例和 auto-human 适用性以本目录 `entry_contract.json` 为准；本文件只解释业务纪律和运行边界。

## 触发规则

- 用户显式输入 `/lgwf-wf-tools self-improve`、`/lgwf-wf-tools 自我优化`，或自然语言要求复盘、自我优化、优化交互体验、沉淀 case、生成 proposal、生成 eval case 时，选择本 workflow；先归类问题、列出可执行的 self-improve 路径，再说明哪些操作需要用户确认。
- 真实运行中出现路由错误、approval 处理错误、监控 handle 丢失、旧 `work_dir` 处理错误或最终报告缺口时，主 agent 只能建议记录 incident；必须用户确认后才能调用 `record_incident.py`。
- 只读类命令可直接执行：`eval`、`workflow-health`、`trace-eval`、`scorecard`、`changed-files`、`pre-release`。
- 记录类命令需要确认：`incident`、`proposal`、`eval-case`。如果用户已经明确要求“记录这次问题”“生成 proposal”或“生成 eval 草稿”，可以把当前对话作为证据直接执行。
- proposal 后续处理必须是两段式：先提醒用户是否查看或执行 proposal，再通过 `/lgwf-wf-tools 优化方案` 展示 review 计划；不直接执行 proposal，执行前必须先展示 review 计划并等待明确批准。
- 发布包变更类操作必须人工批准：`promote-eval`、修改 `SKILL.md`、`AGENTS.md`、`registry.json`、baseline eval 或 workflow 文件。
- `workflow-health` 必须检查 registry 中 `kind=lgwf` 的目标级 self-improve 覆盖率，并执行 `workflow-health/baseline.json` 中每个 workflow 的 `audit_command`；audit 失败时 health 必须失败。
- `workflow-health` 必须把存在 `workflow.lgwf` 但未注册的目录报告为 drift 候选；drift 候选不直接导致失败。

## 本次运行证据优先

当当前对话已经执行或纠正过相关 workflow 时，self-improve 必须先复盘本次运行，不得先用通用 health 检查代替运行复盘：

1. 识别当前对话中的 `workflow_id`、`run_id`、目标目录和用户纠正。
2. 读取每个相关 run 的 `summary.md` 与 `changes.json`；缺失时明确记录缺失项。
3. 读取目标产物、handoff、materialization 摘要和本次验证结果，核对实际写入位置与报告内容。
4. 基于以上证据归类 incident，并在用户确认后生成 proposal 或 eval case。
5. `changed-files`、`eval`、`workflow-health`、`trace-eval` 和 `scorecard` 只能作为补充证据，用于验证影响面和回归风险。

只有当前对话没有相关运行证据时，通用检查才可以作为主要入口。不得因为 health 通过就忽略本次用户纠正或运行产物中的问题。

## 执行入口

```powershell
python workflows/self-improve/scripts/self_improve.py eval --check-overrides
python workflows/self-improve/scripts/self_improve.py workflow-health
python workflows/self-improve/scripts/self_improve.py trace-eval
python workflows/self-improve/scripts/self_improve.py workflow-tests --workflow-id wf-fix
python workflows/self-improve/scripts/self_improve.py pre-release --version <version> --source <source>
python workflows/self-improve/scripts/validate_manifest.py
```

## 产物边界

- 发布包基线保存在 `workflows/self-improve/`。
- 运行期历史、报告、proposal、scorecard 和本地 override 必须写入 facade 根目录 `.local/`。
- self-improve 脚本只生成记录、报告和 proposal，不自动修改 `AGENTS.md`、`registry.json` 或 workflow 文件，也不自动修改 vendor 文件。
- 发布包不得覆盖或删除 `.local/self-improve/`、`.local/overrides/` 或 `.local/upgrade-reports/`。
