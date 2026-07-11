# classify-impact

## step_slug

`classify-impact`

## step_name

分类影响面与风险等级

## goal

设计 `wf/02_classify_impact/workflow.lgwf`，把 `change_context.json` 中的变更文件映射到统一的类别体系、受影响 workflow、风险等级和推荐验证候选。这个阶段的价值是把“改了哪些文件”转成“应该做哪些检查”的可审计中间层，为后续计划生成提供确定性输入。

## inputs

- 上游阶段或节点：
  - `collect-change-context`
  - `.lgwf/business_flow.json` 中 `02_classify_impact` 阶段定义
- 依赖文件或状态：
  - `.lgwf/change_context.json`
  - `docs_tmp/wf-maintenance-gate-development.md`
  - `wf/shared/scripts/maintenance_gate_common.py`
  - `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`
- 关键约束：
  - 至少支持 `facade_entry`、`workflow_source`、`workflow_tests`、`shared_contract`、`scripts`、`self_improve`、`vendor`、`docs_only`、`packaging`
  - 需要输出 `low` / `medium` / `high` 风险等级
  - 需要给出推荐验证候选，但不能直接执行命令

## outputs

- 预期生成的文件：
  - `wf/02_classify_impact/workflow.lgwf`
  - `wf/02_classify_impact/scripts/*.py`
  - `wf/02_classify_impact/resources/*`
  - `.lgwf/impact_classification.json`
- 预期生成的目录：
  - `wf/02_classify_impact/agents/`
  - `wf/02_classify_impact/scripts/`
  - `wf/02_classify_impact/resources/`
- 交付给下游的结构片段：
  - 每个变更文件的分类结果与匹配规则
  - 受影响 workflow id 列表
  - 风险等级与原因
  - 推荐验证候选和其触发来源

## dependencies

- 前置步骤：
  - `define-shared-helper-and-tests`
  - `collect-change-context`
- 依赖节点：
  - registry workflow 列表
  - 共享 helper 中的分类与风险枚举
- 需要人工确认的位置：
  - 当前阶段不引入人工确认；分类歧义只能通过输出结构中的待审备注暴露，不能静默覆盖已知规则

## implementation_suggestions

- 把“路径规则优先 + registry 元数据补充”的混合映射策略固化为脚本逻辑：先按目录前缀和文件名分类，再用 registry 中的 workflow id/path 补充受影响 workflow 判定。
- 对 `vendor`、`shared_contract`、`workflow_source`、`packaging` 这类高风险类别设置更高优先级，避免文件同时命中多个类别时被 `docs_only` 等低风险类别吞掉。
- 风险等级应给出结构化依据，例如“改动 entry_contract / registry / vendor / shared contract => high”，“只改 docs => low”。
- 资源目录中可保存类别说明、workflow 路径映射示例和风险策略说明，方便 tests 和 summary 共用一致文案。

## 修订补充：impact rules 与输出 schema

分类阶段必须把以下规则表固化到脚本或阶段资源中，并在 `impact_classification.json` 中记录命中的规则 id。

| path pattern | category | priority | risk | impacted workflow | recommended checks |
| --- | --- | ---: | --- | --- | --- |
| `skills/lgwf-wf-tools/registry.json` | `facade_entry` | 100 | `high` | `all_workflows` | `doctor`、`deep_doctor` |
| `skills/lgwf-wf-tools/SKILL.md`、`AGENTS.md`、`README.md` | `facade_entry` | 90 | `medium` | `all_workflows` | `doctor` |
| `skills/lgwf-wf-tools/workflows/01-share/**` | `shared_contract` | 100 | `high` | `all_workflows` | `doctor`、`deep_doctor`、`workflow_tests` |
| `skills/lgwf-wf-tools/docs/LGWF_WF_MODULAR_DEVELOPMENT.md` | `shared_contract` | 95 | `high` | `all_workflows` | `doctor`、`deep_doctor` |
| `skills/lgwf-wf-tools/workflows/<id>/wf/**` | `workflow_source` | 90 | `high` | `<id>` | `doctor`、`workflow_tests` |
| `skills/lgwf-wf-tools/workflows/<id>/entry_contract.json` | `workflow_source` | 95 | `high` | `<id>` | `doctor`、`deep_doctor`、`workflow_tests` |
| `skills/lgwf-wf-tools/workflows/<id>/AGENTS.md` | `workflow_source` | 85 | `medium` | `<id>` | `doctor`、`workflow_tests` |
| `skills/lgwf-wf-tools/workflows/<id>/tests/**` | `workflow_tests` | 70 | `medium` | `<id>` | `workflow_tests` |
| `skills/lgwf-wf-tools/workflows/self-improve/**` | `self_improve` | 90 | `high` | `self-improve` | `self_improve_health`、`pre_release` |
| `skills/lgwf-wf-tools/vendor/lgwf-client-assist/**` | `vendor` | 100 | `high` | `all_workflows` | `doctor`、`deep_doctor`、`workflow_tests` |
| `skills/lgwf-wf-tools/scripts/package_lgwf_wf_tools_zip.py`、`scripts/package_lgwf_skill.py`、`workflows/skill-packaging/**` | `packaging` | 90 | `high` | `skill-packaging` | `doctor`、`package_smoke` |
| `skills/lgwf-wf-tools/scripts/**` | `scripts` | 75 | `medium` | `none` | `doctor` |
| 普通 `*.md`、`templates/**` | `docs_only` | 10 | `low` | `none` | `none` |

冲突处理规则：

- 同一文件命中多条规则时保留所有 `matched_rules`，主分类取最高 `priority`；风险取最高等级。
- `docs_only` 只能作为兜底分类，不能覆盖 `AGENTS.md`、`README.md`、共享契约文档、entry contract 或 workflow 源码。
- registry 无法映射 workflow id 时，`impact_classification.json` 必须写入 `ambiguities`，并把总体状态提升为至少 `needs_review` 候选。
- 未跟踪文件、重命名和跨目录移动必须保留 `git_status_code` 或等价来源字段，移动文件按 old path 和 new path 分别分类后合并风险。

`impact_classification.json` 的最小结构：

```json
{
  "files": [
    {
      "path": "skills/lgwf-wf-tools/workflows/wf-create/wf/workflow.lgwf",
      "change_kind": "modified",
      "category": "workflow_source",
      "matched_rules": ["workflow_source_wf"],
      "priority": 90,
      "risk": "high",
      "impacted_workflows": ["wf-create"],
      "recommended_checks": ["doctor", "workflow_tests"],
      "rationale": "workflow.lgwf 变更会影响目标 workflow 的运行拓扑"
    }
  ],
  "impacted_workflows": ["wf-create"],
  "risk": "high",
  "recommended_checks": ["doctor", "workflow_tests"],
  "ambiguities": []
}
```

## acceptance_notes

- 重点确认 changed files 到 target workflows 的判定不是单纯猜测文件名，而是基于路径规则并可用 registry 信息补充。
- 重点确认 `docs_only` 只用于普通 Markdown/模板，不会把 `AGENTS.md`、`entry_contract.json`、`workflow.lgwf` 或 `vendor` 误判为低风险文档改动。
- 重点确认输出中保留“为什么推荐这些验证”的因果链，便于后续 `plan-verification` 直接消费而不是重算。

## out_of_scope

- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 在当前阶段直接执行任何验证命令或写出最终 summary
