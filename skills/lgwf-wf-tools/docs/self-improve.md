# Self Improve 流程

`workflows/self-improve/` 是本 facade 的自我提升 tool workflow，只保存发布包内的 schema、baseline eval、模板和只读脚本。运行期历史、报告、proposal 和本地 override 必须写入 `.local/`，不要放入发布包基线。

## 触发规则

- 用户显式输入 `/lgwf-wf-tools self-improve`、`/lgwf-wf-tools 自我优化`，或自然语言要求复盘、自我优化、优化交互体验、沉淀 case、生成 proposal、生成 eval case 时，根 `AGENTS.md` 必须路由到 `self-improve` workflow；先归类问题、列出可执行的 self-improve 路径，再说明哪些操作需要用户确认。
- 真实运行中出现路由错误、approval 处理错误、监控 handle 丢失、旧 `work_dir` 处理错误或最终报告缺口时，主 agent 只能建议记录 incident；必须用户确认后才能调用 `record_incident.py`。
- 只读类 self-improve 可直接执行：`eval`、`workflow-health`、`trace-eval`、`scorecard`、`changed-files`、`pre-release`。
- `workflow-health` 会执行 `workflow-health/baseline.json` 中的 `audit_command`，并检查 registry、目标级 self-improve 覆盖率、共享语义要求和未注册 workflow drift；audit 失败时 health 失败。
- 记录类 self-improve 需要确认：`incident`、`proposal`、`eval-case`。如果用户已经明确要求“记录这次问题/生成 proposal/生成 eval 草稿”，可以把当前对话作为证据直接执行。
- proposal 后续处理必须是两段式：先提醒用户是否查看或执行 proposal，再通过 `/lgwf-wf-tools 优化方案` 展示 review 计划；不直接执行 proposal，执行前必须先展示 review 计划并等待明确批准。
- 发布包变更类 self-improve 必须人工批准：`promote-eval`、修改 `SKILL.md`、`AGENTS.md`、`registry.json`、baseline eval 或 workflow 文件。
- self-improve 脚本只生成记录、报告和 proposal，不自动修改 `AGENTS.md`、`registry.json`、workflow 文件或 vendor 文件。

## 固定产出

- `.local/self-improve/incidents/*.json`：用户确认后的真实问题记录。
- `.local/self-improve/reports/*self-eval.json` 和 `.md`：确定性 self eval 结果。
- `.local/self-improve/reports/*trace-eval.json` 和 `.md`：固定 LGWF runtime workflow 的 trace eval 结果，包含 `trace.json`、`eval-suite.json`、failed case、failed check 和 policy risk 摘要。
- `.local/self-improve/proposals/*.md`：基于 incident 或 eval report 生成的可审查改进提案。
- `.local/self-improve/scorecards/*.md`：周期复盘指标。
- `.local/overrides/AGENTS.local.md` 和 `.local/overrides/*.json`：本地私有 override，仅允许补充或收紧规则。

发布包不得覆盖或删除 `.local/self-improve/`、`.local/overrides/` 或 `.local/upgrade-reports/`。

## 常用命令

```powershell
python workflows\self-improve\scripts\run_self_evals.py
python workflows\self-improve\scripts\run_self_evals.py --changed-files <changed-files.json> --check-overrides
python workflows\self-improve\scripts\self_improve.py eval --check-overrides
python workflows\self-improve\scripts\self_improve.py workflow-health
python workflows\self-improve\scripts\self_improve.py trace-eval
python workflows\self-improve\scripts\self_improve.py workflow-tests --workflow-id wf-fix
python workflows\self-improve\scripts\self_improve.py pre-release --version <version> --source <source>
python workflows\self-improve\scripts\self_improve.py workflow-proposal --workflow-id <id> --health-report <report.json> --eval-report <eval.json> --trace-eval-report <trace-eval.json>
python workflows\self-improve\scripts\validate_manifest.py
```

`eval`、`workflow-health` 和 `trace-eval` 不评价同一件事：`eval` 检查 facade 规则、baseline 和本地 override 风险；`workflow-health` 执行 baseline audit 并检查 registry / workflow 结构；`trace-eval` 消费 LGWF runtime 的 `trace.json` 和 `eval-suite.json`，检查真实运行轨迹、client call、catalog policy 和 unexpected route。`pre-release` 默认会在 `workflow-health` 之后运行 `trace-eval`，再生成 scorecard 和 upgrade report。
