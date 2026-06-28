# 自我提升闭环

`lgwf-wf-agent` 的自我提升采用证据驱动闭环：

1. `observe`：收集用户纠正、失败 run、approval 卡点、路由争议、最终报告缺口。
2. `classify`：归类为 routing、monitoring、approval、input_contract、reporting、release 或 docs。
3. `evaluate`：把问题映射到 baseline 或新增 eval case，并运行 `scripts/run_self_evals.py`。
4. `propose`：基于 incident 或 eval report 生成 proposal，说明证据、根因、拟修改文件、验证方式和风险。
5. `approve`：用户明确批准后，才允许进入普通修改流程。
6. `apply`：小步修改发布文件；运行期历史继续保存在 `.local/`。
7. `verify`：运行 self eval 和对应 workflow package 自检。
8. `record`：把结果写入 `.local/self-improve/reports/` 或 `.local/self-improve/scorecards/`。

## 变更触发

当 changed files 命中以下模式时，必须运行 self eval：

- `SKILL.md`
- `AGENTS.md`
- `registry.json`
- `workflows/*/AGENTS.md`
- `workflows/**/workflow.lgwf`
- `scripts/init_lgwf_wf_agent.py`
- `scripts/doctor_lgwf_wf_agent.py`
- `vendor/lgwf-client-assist/.lgwf-client-assist-vendor.json`

第二版由 `run_self_evals.py --changed-files <json>` 记录命中原因。`<json>` 是字符串数组，可以是相对 facade root 的路径。

第三版可以先运行：

```powershell
python self-improve\scripts\collect_changed_files.py --output .local\self-improve\changed-files.json
python self-improve\scripts\run_self_evals.py --changed-files .local\self-improve\changed-files.json --check-overrides
```

## Eval Case 草稿

真实 incident 经用户确认后，可以用 `create_eval_case.py` 生成草稿。草稿默认写入 `.local/self-improve/eval-case-drafts/`，需要人工审查后才允许复制进 `self-improve/evals/` 作为发布包 baseline。

## Scorecard

周期复盘或发布前可以运行：

```powershell
python self-improve\scripts\generate_scorecard.py
```

Scorecard 只汇总指标，不自动创建 proposal，也不自动修改规则。

## 发布前聚合检查

第四版提供聚合入口：

```powershell
python self-improve\scripts\pre_release_check.py --version <version> --source <source>
```

该命令会依次运行 changed-files 收集、self eval、scorecard 和 upgrade report，并写入 `.local/self-improve/pre-release/`。如果任一步失败，整体返回失败。

## 提升 Eval Baseline

只有人工审查通过的 eval draft 可以提升为 baseline：

```powershell
python self-improve\scripts\promote_eval_case.py --draft <draft.json> --approved-by <user>
```

该命令要求 draft case 的 `review_status` 为 `draft`，输出到 `self-improve/evals/promoted-*.json`。它不会修改 `AGENTS.md`、`registry.json`、workflow 或 vendor。

## 统一入口

第五版提供 manifest 驱动的统一入口：

```powershell
python self-improve\scripts\self_improve.py eval --check-overrides
python self-improve\scripts\self_improve.py pre-release --version <version> --source <source>
python self-improve\scripts\self_improve.py scorecard
```

`self-improve/manifest.json` 是命令索引和发布保护策略的机器可读来源。新增 self-improve 脚本时必须同步更新 manifest，并确保 `validate_manifest.py` 通过。

## 禁止事项

- 不基于单次主观感受直接改 facade。
- 不自动 approve 任何会修改目标 package 或发布文件的操作。
- 不把 `.local/` 内容当作发布源文件。
- 不绕过 `vendor/lgwf-client-assist` 的主 agent loop、approval 和 run artifacts 指引。
