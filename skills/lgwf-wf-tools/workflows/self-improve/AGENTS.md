# Self Improve Workflow

本目录是 `lgwf-wf-tools` facade 下的内部 `tool-workflow`，职责是对 facade 自身进行自我评估、真实问题沉淀、proposal 生成、eval case 草稿和发布前检查。它不是 LGWF runtime workflow，不包含 `workflow.lgwf`，不得作为独立 Codex skill 注册。

## 共用规则

执行本 workflow 前必须读取：

- `../01-share/AGENTS.md`
- `../01-share/registry-contract.md`
- `../01-share/tool-workflow.md`
- `../01-share/artifacts.md`

## 触发规则

- 用户显式输入 `/lgwf-wf-tools self-improve`、`/lgwf-wf-tools 自我优化`，或自然语言要求复盘、自我优化、优化交互体验、沉淀 case、生成 proposal、生成 eval case 时，选择本 workflow；先归类问题、列出可执行的 self-improve 路径，再说明哪些操作需要用户确认。
- 真实运行中出现路由错误、approval 处理错误、监控 handle 丢失、旧 `work_dir` 处理错误或最终报告缺口时，主 agent 只能建议记录 incident；必须用户确认后才能调用 `record_incident.py`。
- 只读类命令可直接执行：`eval`、`workflow-health`、`trace-eval`、`scorecard`、`changed-files`、`pre-release`。
- 记录类命令需要确认：`incident`、`proposal`、`eval-case`。如果用户已经明确要求“记录这次问题”“生成 proposal”或“生成 eval 草稿”，可以把当前对话作为证据直接执行。
- proposal 后续处理必须是两段式：先提醒用户是否查看或执行 proposal，再通过 `/lgwf-wf-tools 优化方案` 展示 review 计划；不直接执行 proposal，执行前必须先展示 review 计划并等待明确批准。
- 发布包变更类操作必须人工批准：`promote-eval`、修改 `SKILL.md`、`AGENTS.md`、`registry.json`、baseline eval 或 workflow 文件。

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
