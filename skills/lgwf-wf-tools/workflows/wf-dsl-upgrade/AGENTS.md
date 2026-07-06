# LGWF Workflow DSL Upgrade 指引

本目录是 `lgwf-wf-tools` facade 下的内部 workflow package，用于对已授权的 LGWF workflow 批量执行 DSL 升级草稿流程。它不是独立 Codex skill，只能由 facade 通过 `registry.json` 派发到 `wf/workflow.lgwf`。

## 模块契约

- 模块类型：`lgwf_workflow_package`。
- 执行前应读取 `../01-share/module-contract.md`、`../01-share/registry-contract.md`、`../01-share/lgwf-dispatch.md`、`../01-share/lgwf-monitor.md`、`../01-share/approval.md` 和 `../01-share/artifacts.md`。
- 入口字段、输入示例和 `--auto-human` 策略以本目录 `entry_contract.json` 为准；本文件只解释业务纪律和运行边界。
- 根 `wf/workflow.lgwf` 只编排第一层子 workflow，不在根目录生成可运行 `workflow.lgwf`。

## 模块定位

- 面向 DSL 兼容性升级，不运行业务 workflow。
- 第一版只支持“目标收集、静态 audit、诊断分类、升级计划、人审闸门、受控写入、复检、总结”八个阶段。
- 自动修改仅允许规则化脚本执行；不接入自由形式自愈。

## 入口

- registry id：`wf-dsl-upgrade`
- workflow 入口：`wf/workflow.lgwf`
- work dir：`ws/`

## 依赖

- 依赖 `vendor/lgwf-client-assist/scripts/lgwf.py` 执行 authoring audit。
- 依赖 facade 提供的共享 approval 规则和 bundled client。
- 依赖外部传入的升级目标、范围模式、升级规则配置与执行 mode。

## 状态边界

- 运行状态只允许写入 `ws/.lgwf/` 与 `ws/reports/`。
- workflow 源码树不写入 `.lgwf/`、临时目录或运行摘要。
- 所有 workflow、脚本、资源路径都必须保持包内相对路径。

## 产物

- `.lgwf/target_manifest.json`
- `.lgwf/target_scope_validation.json`
- `.lgwf/batch_audit_result.json`
- `.lgwf/batch_audit_stats.json`
- `.lgwf/classified_findings.json`
- `.lgwf/classification_summary.json`
- `.lgwf/upgrade_plan.json`
- `.lgwf/upgrade_plan_summary.json`
- `.lgwf/upgrade_plan_confirmation_context.json`
- `.lgwf/upgrade_plan_approval.json`
- `.lgwf/applied_changes.json`
- `.lgwf/applied_target_manifest.json`
- `.lgwf/post_upgrade_audit_result.json`
- `.lgwf/post_upgrade_diff_summary.json`
- `.lgwf/result_summary.json`
- `reports/wf-dsl-upgrade/report.md`

## 验证

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\wf\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\tests
```

## 禁止事项

- 不得把 `wf-dsl-upgrade` 注册成独立 Codex skill。
- 不得越过 `target_manifest.json` 授权范围写入文件。
- 不得在 `mode=dry_run`、审批 `reject` 或未审批时执行真实写入。
- 不得创建孙级 `workflow.lgwf`。
- 不得把绝对路径、盘符路径或 `..` 写入 workflow 资源引用。
