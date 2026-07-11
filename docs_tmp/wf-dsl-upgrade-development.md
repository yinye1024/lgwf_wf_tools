# wf-dsl-upgrade 工作流开发文档

## 文档用途

本文用于提交给 `wf-create`，作为重新创建 `skills/lgwf-wf-tools/workflows/wf-dsl-upgrade` 的输入资料。目标是清理旧的占位实现后，由 `wf-create` 按本文重新生成一个真实可运行、可审计、可测试的内部 `lgwf_workflow_package`。

`wf-create` 启动时应把本文作为 `request.target_file`，并以本文的“目标形态”和“验收要求”为准进行需求确认、业务流确认、步骤设计和初稿实现。

## 目标模块

- 模块 id：`wf-dsl-upgrade`
- 模块类型：`lgwf_workflow_package`
- 目标目录：`skills/lgwf-wf-tools/workflows/wf-dsl-upgrade`
- workflow root：`skills/lgwf-wf-tools/workflows/wf-dsl-upgrade/wf`
- workflow 入口：`skills/lgwf-wf-tools/workflows/wf-dsl-upgrade/wf/workflow.lgwf`
- work dir：`skills/lgwf-wf-tools/workflows/wf-dsl-upgrade/ws`
- registry entry：保留 `skills/lgwf-wf-tools/registry.json` 中 id 为 `wf-dsl-upgrade` 的条目，不注册为独立 Codex skill。

## 背景与当前问题

`wf-dsl-upgrade` 的定位是对已授权的 LGWF workflow 执行 DSL 兼容性升级。现有目录已经有八阶段草稿和部分测试，但仍属于占位实现：

- `02_batch_audit` 没有真正调用 `lgwf.py audit`，只写入 `status=placeholder`。
- `03_classify_findings` 不解析真实 audit 诊断，只把目标统一归为 `manual_review`。
- `04_build_upgrade_plan` 不生成可执行规则计划，只在没有 `auto_fixable` 时产出空计划。
- `06_apply_upgrade_rules` 不做真实写入，即使审批通过也只产出 placeholder。
- `07_batch_verify` 不做真实 post-audit，只根据 seeded 状态返回占位结果。
- `08_summarize_upgrade_result` 的报告明确说明“初稿占位”。
- `tests/test_upgrade_rule_pipeline.py` 仍依赖 `wf/wf_01_collect_targets_placeholder.py` 的 sentinel。
- 源码目录下出现 `.lgwf/`、`__pycache__/` 等运行态或缓存文件，违反源码与状态分离要求。

因此本次重建不应在旧实现上继续补丁式修复，而应让 `wf-create` 重新创建一个真实 workflow 包。

## 总体目标

创建一个用于 DSL 升级的内部 workflow，支持：

1. 接收授权范围内的目标 workflow 列表或 registry 范围。
2. 校验目标路径和允许写入目录，生成不可越权的 `target_manifest.json`。
3. 对目标 workflow 批量执行 `lgwf.py audit`，收集结构化诊断和命令结果。
4. 按诊断类型分类为可自动修复、需人工处理、不可支持三类。
5. 根据内置规则生成可审查的升级计划。
6. 在真实写入前展示人工确认，用户明确批准后才允许 apply。
7. 在 `mode=dry_run` 时只生成计划和报告，不修改目标文件。
8. 在 `mode=apply` 且审批通过时，仅修改 `target_manifest.json` 授权范围内的目标文件。
9. 写入后执行 post-audit 和 diff summary，确认修复效果。
10. 生成机器可读 summary 和面向人的报告。

## 非目标

- 不负责运行业务 workflow，只做 authoring audit 和 DSL 兼容性升级。
- 不处理未授权目录或未列入 manifest 的文件。
- 不在 `mode=dry_run` 下写入目标文件。
- 不自动批准升级计划。
- 不引入自由形式自愈或任意 Codex 写文件行为。
- 不把 `wf-dsl-upgrade` 注册为独立 Codex skill。
- 不把 runtime 状态写入 workflow 源码目录。

## 输入契约

入口 JSON 必须以 `entry_contract.json` 为准，核心字段如下：

```json
{
  "dsl_upgrade_target": {
    "target_paths": ["D:/example/workflow.lgwf"],
    "mode": "dry_run",
    "allowed_dirs": ["D:/example"],
    "scope_mode": "explicit",
    "max_targets": 8
  }
}
```

字段说明：

- `target_paths`：显式目标 workflow 文件列表。每个文件必须存在，并且必须位于 `allowed_dirs` 中。
- `mode`：`dry_run` 或 `apply`。缺省使用 `dry_run`。
- `allowed_dirs`：允许读取和写入的目录边界。`apply` 模式下必须提供。
- `scope_mode`：目标收集模式，建议支持 `explicit` 和 `registry`。第一版可以优先实现 `explicit`，但 registry 模式的契约应保留。
- `max_targets`：最大处理目标数，用于防止误扫过大范围。

## 输出契约

机器可读产物写入 `ws/.lgwf/`：

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

面向人的报告写入：

- `ws/reports/wf-dsl-upgrade/report.md`

源码目录必须只保存 workflow、脚本、资源、测试和入口文档，不保存 `.lgwf/`、`__pycache__/` 或运行临时文件。

## 推荐目录结构

```text
wf-dsl-upgrade/
  AGENTS.md
  README.md
  entry_contract.json
  tests/
  ws/
  wf/
    workflow.lgwf
    artifact_contracts.json
    shared/
      scripts/
        dsl_upgrade_common.py
    01_collect_targets/
      workflow.lgwf
      agents/
      resources/
      scripts/
    02_batch_audit/
      workflow.lgwf
      agents/
      resources/
      scripts/
    03_classify_findings/
      workflow.lgwf
      agents/
      resources/
      scripts/
    04_build_upgrade_plan/
      workflow.lgwf
      agents/
      resources/
      scripts/
    05_confirm_upgrade_plan/
      workflow.lgwf
      agents/
      resources/
      scripts/
    06_apply_upgrade_rules/
      workflow.lgwf
      agents/
      resources/
      scripts/
    07_batch_verify/
      workflow.lgwf
      agents/
      resources/
      scripts/
    08_summarize_upgrade_result/
      workflow.lgwf
      agents/
      resources/
      scripts/
```

根 `wf/workflow.lgwf` 只做薄编排，阶段内部逻辑必须落在对应 `wf/<stage>/workflow.lgwf`、`scripts/`、`resources/` 和 `agents/` 中。不得创建孙级 `workflow.lgwf`。

## 阶段设计

### 01_collect_targets

目标：解析入口输入，校验目标范围，生成授权 manifest。

实现要求：

- 读取 `dsl_upgrade_target.target_paths`、`allowed_dirs`、`mode`、`scope_mode` 和 `max_targets`。
- 规范化路径，但写入 manifest 时保留可审查的原始路径和 resolved path。
- 校验目标必须存在、必须是 `workflow.lgwf`，并且必须位于 `allowed_dirs` 中。
- `mode=apply` 时如果缺少 `allowed_dirs`，必须失败或标记 validation failed，不能继续写入阶段。
- 生成 `target_manifest.json`，包含目标列表、hash、mode、allowed_dirs、scope_mode、max_targets、authorized。
- 生成 `target_scope_validation.json`，包含 `passed`、`reasons`、`target_count`。

### 02_batch_audit

目标：对 manifest 中每个目标执行真实 `lgwf.py audit`。

实现要求：

- 使用 facade 内置 `vendor/lgwf-client-assist/scripts/lgwf.py audit <target>`。
- 每个目标记录 returncode、stdout 摘要、stderr 摘要、audit JSON、passed 状态和诊断列表。
- 单个目标失败不应丢失其他目标结果；批次结果必须完整记录。
- 输出 `batch_audit_result.json` 和 `batch_audit_stats.json`。

### 03_classify_findings

目标：把 audit 诊断分类为可自动修复、人工处理和不支持。

实现要求：

- 根据 audit 输出中的错误类型、节点、字段和 resource path 生成分类。
- 第一版至少支持可确定的规则分类，例如 resource path 违规、旧 DSL 字段名、缺失 contract 字段、旧 approval/human 节点写法。
- 无法安全自动处理的诊断必须归入 `manual_review`，不得伪装为可修复。
- 输出 `classified_findings.json` 和 `classification_summary.json`。

### 04_build_upgrade_plan

目标：把可自动修复项转换为可审查升级计划。

实现要求：

- 每个 plan item 必须包含 `target_file`、`rule_id`、`risk`、`change_summary`、`expected_impact`、`pre_hash` 和 `planned_actions`。
- 计划必须可读、可审查，且只引用 manifest 授权目标。
- 如果没有可自动修复项，仍应生成空计划和原因说明。
- 输出 `upgrade_plan.json` 和 `upgrade_plan_summary.json`。

### 05_confirm_upgrade_plan

目标：在任何真实写入前取得人工确认。

实现要求：

- 使用共享 approval 展示模板，不能只问一句“是否确认”。
- 展示确认原因、影响范围、目标数量、计划项、风险、dry_run/apply 差异、提交值和后续动作。
- 支持 `approve`、`revise`、`reject`。
- `approve` 是纯决策，不携带业务 JSON；节点自行固化已展示 proposal。
- `revise` 需要完整修订值，并重新进入同一 review 节点。
- 输出 `upgrade_plan_confirmation_context.json` 和 `upgrade_plan_approval.json`。

### 06_apply_upgrade_rules

目标：在授权模式下应用确定性升级规则。

实现要求：

- 只有 `mode=apply` 且审批结果为 `approve` 时才允许写入。
- 写入前再次校验目标在 `target_manifest.json` 中，且位于 `allowed_dirs`。
- 每个目标写入前记录 `pre_hash`，写入后记录 `post_hash`。
- 不允许对未列入 plan 的文件做修改。
- 不支持的规则必须跳过并记录原因。
- 输出 `applied_changes.json` 和 `applied_target_manifest.json`。

### 07_batch_verify

目标：对已修改目标执行 post-audit 并生成差异摘要。

实现要求：

- 对 `applied_target_manifest.json` 中实际修改的目标再次执行 `lgwf.py audit`。
- 比较 pre/post audit 诊断，统计 resolved、remaining、new findings。
- 输出 `post_upgrade_audit_result.json` 和 `post_upgrade_diff_summary.json`。

### 08_summarize_upgrade_result

目标：汇总本次升级结果，生成机器 summary 和 Markdown 报告。

实现要求：

- 汇总目标范围、mode、审批结果、计划项、应用项、复检结果和剩余风险。
- 报告必须明确列出未处理目标、跳过原因和建议下一步。
- `result_summary.json` 的 `status` 应区分 `dry_run`、`applied`、`skipped`、`failed` 或 `partial`，不能继续使用 `draft`。
- 输出 `result_summary.json` 和 `reports/wf-dsl-upgrade/report.md`。

## 共享 helper 要求

`wf/shared/scripts/dsl_upgrade_common.py` 可以包含：

- UTF-8 JSON 读写。
- 路径规范化与 allowed_dirs 校验。
- manifest 读写。
- `lgwf.py audit` 调用封装。
- hash 计算。
- stdout/stderr 摘要裁剪。

共享 helper 只能承载稳定技术逻辑，不得包含阶段私有 prompt、approval 文案或业务决策。

## 人工确认边界

- 本 workflow 只有升级计划确认一个人工闸门。
- `dry_run` 可以走完整流程，但必须跳过真实写入。
- `apply` 必须经过人工确认后才能写入。
- `reject` 必须阻止写入，但可以进入总结阶段生成报告。
- `revise` 不得直接写入目标文件。

## 验证要求

最小验证命令：

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\wf\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\tests
```

测试至少覆盖：

- root workflow 只编排八个第一层子 workflow。
- 每个阶段目录自包含 `workflow.lgwf`、`agents/`、`scripts/`、`resources/`。
- `dry_run` 不修改目标文件。
- `apply + approve` 只修改 manifest 授权文件。
- `apply + reject` 不修改目标文件。
- `allowed_dirs` 越界时终止或 validation failed。
- batch audit 调用真实 `lgwf.py audit` 并保留失败诊断。
- post-audit 能识别 resolved、remaining 和 new findings。
- 报告不再出现“占位”“placeholder”“draft”等初稿用语，除非是在测试 fixture 中明确断言旧行为不可接受。

## 旧内容清理要求

在启动 `wf-create` 前，旧 `wf-dsl-upgrade` 源码内容应清理，避免 `wf-create` 继承占位实现。清理范围：

- 删除旧的 `AGENTS.md`、`README.md`、`entry_contract.json`、`scripts/`、`tests/`、`self-improve/` 和 `wf/`。
- 删除旧源码树中的 `.lgwf/`、`__pycache__/` 和占位脚本。
- 保留 `ws/` 目录作为运行状态目录；如有历史 run，不在本次清理中删除。

`wf-create` 应重新生成目标 package 必备入口文档、`entry_contract.json`、`wf/artifact_contracts.json`、stage workflow、脚本、资源和测试。

## 验收标准

重建完成后必须满足：

- `registry.json` 中 `wf-dsl-upgrade` 条目仍指向存在的 `AGENTS.md`、`entry_contract.json` 和 `wf/workflow.lgwf`。
- `wf/workflow.lgwf` audit 通过。
- `python -m unittest discover skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\tests` 通过。
- 源码目录不包含 `.lgwf/`、`__pycache__/` 或运行输出。
- `README.md`、`AGENTS.md` 和 `entry_contract.json` 的模块定位、入口、依赖、状态边界、产物、验证和禁止事项一致。
- dry_run、apply approve、apply reject 三类路径都有测试覆盖。
