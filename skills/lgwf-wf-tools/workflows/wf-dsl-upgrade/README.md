# wf-dsl-upgrade

`wf-dsl-upgrade` 是 `lgwf-wf-tools` facade 内部使用的 `lgwf_workflow_package`。它面向已授权的 LGWF workflow 目录，执行静态 DSL 升级草稿流程：收集目标、批量 audit、分类诊断、生成升级计划、人工确认、受控应用、复检与总结。

## 目录结构

```text
wf-dsl-upgrade/
  AGENTS.md
  README.md
  scripts/
  tests/
  ws/
  wf/
    workflow.lgwf
    shared/scripts/
    01_collect_targets/
    02_batch_audit/
    03_classify_findings/
    04_build_upgrade_plan/
    05_confirm_upgrade_plan/
    06_apply_upgrade_rules/
    07_batch_verify/
    08_summarize_upgrade_result/
```

`wf/` 是唯一 workflow root。根 workflow 只编排八个第一层子 workflow；阶段内部逻辑全部放在各自的 `wf/<stage>/workflow.lgwf` 中。

## 输入边界

- `scope_mode`、`target_roots`、`target_workflow_lgwfs`、`include_workflow_ids`、`exclude_workflow_ids`、`max_targets`
- `mode=dry_run|apply`
- `upgrade_profile`
- 其他上下文由外部 workflow 或 facade 通过 state / input 注入

## 输出边界

- 机器可读产物写入 `ws/.lgwf/`
- 面向人的报告写入 `ws/reports/wf-dsl-upgrade/`
- 源码树只保存 workflow、脚本、资源和测试，不保存运行态

## 最小验证

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\wf\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\tests
```
