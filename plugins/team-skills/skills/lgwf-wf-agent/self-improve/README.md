# lgwf-wf-agent 自我提升工作台

本目录保存 `lgwf-wf-agent` 的自我提升基线、评测定义、模板和只读工具。它不是自动修改自身的 workflow，也不是运行期状态目录。

## 目标

- 把真实失败、用户纠正和发布前检查沉淀为可回归的评测样例。
- 让每次改动 `SKILL.md`、`AGENTS.md`、`registry.json` 或内部 workflow 指引后，都能做确定性回归。
- 生成可审查的改进 proposal，而不是无证据地自动修改 facade。

## 触发方式

- 用户主动要求复盘、沉淀 case、生成 proposal 或运行 self eval 时，由 `lgwf-wf-agent` skill 触发。
- 修改 facade 或内部 workflow 指引后，由本地脚本或 CI 运行 `scripts/run_self_evals.py`。
- 真实运行中出现路由、approval、监控或报告问题时，主 agent 只能建议记录 incident；用户确认后再记录。
- 发布前运行 `self_improve.py pre-release`；升级后写入 upgrade report。

## 触发矩阵

| 场景 | 推荐命令 | 边界 |
| --- | --- | --- |
| 使用 `/lgwf-wf-agent` 前 | `python scripts\doctor_lgwf_wf_agent.py` | 只读检查安装状态，不修改文件。 |
| vendor zip 更新 | `python scripts\init_lgwf_wf_agent.py` 后运行 `python scripts\doctor_lgwf_wf_agent.py` | `init` 有副作用，只用于同步 bundled client。 |
| 开发期修改 facade 或内部 workflow | `python self-improve\scripts\self_improve.py workflow-health` 或 `python self-improve\scripts\self_improve.py eval --check-overrides` | 检查结构、语义、路由、approval 和 override 风险。 |
| 发布前默认 gate | `python self-improve\scripts\self_improve.py pre-release --version <version> --source package` | 自动包含 doctor 和 workflow health；不自动 init。 |
| 发布前严格 gate | `python self-improve\scripts\self_improve.py pre-release --version <version> --source package --run-workflow-tests` | 额外执行内部 workflow tests，可能更慢。 |

`pre-release` 是发布前 gate，不是安装修复工具。doctor 失败时，pre-release 必须失败；如果需要同步 vendor，应先由人工或外部发布流程执行 `init -> doctor`，再重新运行 pre-release。

## 发布与本地状态

发布包可以覆盖本目录中的 schema、baseline eval 和模板。运行期产物必须写入：

```text
.local/self-improve/incidents/
.local/self-improve/reports/
.local/self-improve/proposals/
.local/self-improve/scorecards/
.local/overrides/
.local/upgrade-reports/
```

`.local/` 必须被保留，不应被发布覆盖或清理。

## 第一版边界

- 只做确定性检查，不调用 LLM judge。
- 只生成 incident、report 和 proposal，不自动修改 `AGENTS.md`、`registry.json` 或 workflow 文件。
- 所有 apply 都必须由用户明确批准并通过普通编辑流程完成。

## 第二版能力

- `scripts/run_self_evals.py --changed-files <json>`：根据改动文件判断是否触发 self eval，并把触发原因写入报告。
- `scripts/run_self_evals.py --check-overrides`：扫描 `.local/overrides/` 中的明显高风险规则，生成 override findings。
- `scripts/write_upgrade_report.py`：发布或升级后生成 `.local/upgrade-reports/*-upgrade.md`，记录 vendor manifest、zip hash、`.local` 保留状态和 override 风险。

## 第三版能力

- `scripts/collect_changed_files.py --output <json>`：从当前 git worktree 收集 facade 内的 changed files，供 self eval 使用。
- `scripts/create_eval_case.py --incident <incident.json>`：把用户确认后的 incident 转成待审核 eval case 草稿，写入 `.local/self-improve/eval-case-drafts/`。
- `scripts/generate_scorecard.py`：汇总 `.local/self-improve/` 中的 incidents、reports 和 proposals，生成 scorecard JSON/Markdown。

## 第四版能力

- `scripts/pre_release_check.py`：串联 changed files 收集、self eval、scorecard 和 upgrade report，生成 pre-release 汇总报告。
- `scripts/promote_eval_case.py --draft <draft.json> --approved-by <user>`：在人工批准后把 eval draft 提升为 baseline eval 文件。该脚本只提升 eval case，不修改 routing、workflow 或 vendor。

## 第五版能力

- `manifest.json`：机器可读入口，列出命令、发布保护策略和本地状态目录。
- `scripts/self_improve.py <command>`：统一命令入口，按 manifest 转发到具体脚本。
- `scripts/validate_manifest.py`：校验 manifest、命令脚本、发布保护和 `.gitignore`。
- `run_self_evals.py` 会自动执行 manifest 校验。

## 第六版能力

- `overrides/schema.json`：约束 `.local/overrides/*.json` 只能补充或收紧规则；禁止替换核心 workflow、绕过 approval、fallback 外部 skill 或覆盖 vendor 指引。
- `scripts/run_self_evals.py --check-overrides`：同时扫描 override 文本中的高风险词和 JSON key 白名单。
- `workflow-health/baseline.json`：记录四个内部 workflow 的职责基线、自检命令和已知 blocker。
- `scripts/check_workflow_health.py`：确定性检查 `registry.json`、workflow 入口、内部 `AGENTS.md`、`work_dir`、测试目录和内部 `SKILL.md` 禁令。
- `scripts/create_workflow_improvement_proposal.py`：根据 health report 和可选 incident 生成 `.local/self-improve/proposals/*workflow-<id>.md`，只供人工审查。
- `scripts/pre_release_check.py`：发布前 gate 现在包含 doctor 和 workflow health 检查。

## 第七版能力

- Workflow health 增加 `semantic_requirements`：每个内部 workflow 的 `AGENTS.md` 必须说明不负责什么、何时需要 approval、产出文件在哪里、失败时如何由 facade 路由。
- `scripts/run_workflow_tests.py`：按 `workflow-health/baseline.json` 中的 `test_command` 执行内部 workflow 自身测试，输出结构化报告。它不会默认进入 pre-release，避免发布 gate 变慢或卡在运行环境问题上。
- `scripts/pre_release_check.py --run-workflow-tests`：发布前手动开启内部 workflow tests；每条命令有 timeout。
- `scripts/create_workflow_improvement_proposal.py` 可合并 health report、incident、eval report 和 changed files，输出问题证据、影响范围、推荐修改文件、验收命令和是否需要用户 approval。
- `scripts/generate_scorecard.py` 增加趋势字段：最近 incident 类型分布、重复失败 workflow、路由误判次数和 approval 卡点次数。

## 常用命令

```powershell
python self-improve\scripts\self_improve.py eval --check-overrides
python self-improve\scripts\self_improve.py pre-release --version <version> --source release
python self-improve\scripts\self_improve.py pre-release --version <version> --source release --run-workflow-tests
python self-improve\scripts\record_incident.py --type <type> --summary "..." --evidence-json "[...]"
python self-improve\scripts\create_eval_case.py --incident <incident.json>
python self-improve\scripts\self_improve.py workflow-health
python self-improve\scripts\self_improve.py workflow-health --workflow-id wf-fix
python self-improve\scripts\self_improve.py workflow-tests --workflow-id wf-fix
python self-improve\scripts\self_improve.py workflow-proposal --workflow-id <id> --health-report <report.json> --incident <incident.json> --eval-report <eval.json> --changed-files <changed-files.json>
python self-improve\scripts\validate_manifest.py
```

## Workflow Health 边界

- 只检查 facade 内部 workflow package 的确定性结构问题，不运行目标业务 workflow。
- 语义检查只检查 `AGENTS.md` 中是否存在必要说明，不判断文案质量；需要进一步修改时生成 proposal。
- 发现问题只生成 report 或 proposal；是否修改对应 workflow 由用户另行批准。
- 内部 workflow 目录不得包含 `SKILL.md`；对外入口仍然只允许根目录 `SKILL.md`。
- `workflow-health/baseline.json` 是发布包基线；运行期报告写入 `.local/self-improve/reports/`。
