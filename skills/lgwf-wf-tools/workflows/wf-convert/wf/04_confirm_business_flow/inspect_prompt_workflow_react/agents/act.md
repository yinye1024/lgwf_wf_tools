# Act slot：生成 inspection

## 角色

你负责按照 reason 计划生成固定结构的 prompt workflow inspection。

## 输入

- `.lgwf/prompt_file_index.json`
- `.lgwf/prompt_workflow_inspection_reason.json`

## 输出

只输出 `.lgwf/prompt_workflow_inspection.json` 对应的 UTF-8 JSON object。顶层字段固定为：

```json
{
  "source_summary": [],
  "detected_stages": [],
  "prompt_contracts": [],
  "source_business_contract": {
    "goal": "",
    "inputs": [],
    "outputs": [],
    "stages": [],
    "decision_rules": [],
    "approval_points": [],
    "error_paths": [],
    "invariants": []
  },
  "prompt_execution_mechanics": [],
  "presentation_constraints": [],
  "discarded_prompt_techniques": [],
  "human_approval_points": [],
  "gaps": [],
  "risks": [],
  "assumptions": []
}
```

## 固定条目契约

`source_summary`：

```json
{"path": "README.md", "role": "入口说明", "evidence": "支持何种事实的摘要"}
```

`detected_stages`：

```json
{
  "stage_id": "collect_input",
  "name": "收集输入",
  "responsibility": "阶段职责",
  "inputs": [],
  "outputs": [],
  "source_files": ["README.md"],
  "evidence_strength": "high",
  "proposal_consumer": ["raw_intent", "stages"],
  "degrade_target": "none",
  "evidence_summary": "来源中支持该阶段的具体线索"
}
```

`prompt_contracts`：

```json
{
  "prompt_path": "agents/example.md",
  "responsibility": "prompt 职责",
  "inputs": [],
  "outputs": [],
  "constraints": [],
  "source_files": ["agents/example.md"],
  "evidence_strength": "high",
  "proposal_consumer": ["prompt_contracts"],
  "degrade_target": "none",
  "evidence_summary": "支持职责和契约的具体线索"
}
```

`source_business_contract` 除 `goal` 外的每个条目固定为：

```json
{
  "rule_id": "decision_rule_001",
  "statement": "可验证业务规则",
  "source_files": ["README.md"],
  "evidence_strength": "high"
}
```

`gaps` 和 `risks`：

```json
{
  "id": "gap_001",
  "category": "missing_contract",
  "description": "缺口或风险",
  "blocking_scope": "approval",
  "severity": "high",
  "impact_chain": "如何影响 proposal、approval 或 handoff target"
}
```

## 枚举

- `evidence_strength`：`high|medium|low`
- `proposal_consumer`：`raw_intent|stages|prompt_contracts|human_approval_points|approval_reference|assumptions|gaps`
- `degrade_target`：`none|assumptions|human_approval_points|gaps|run_workflow_notes_for_wf_create_fast`
- `blocking_scope`：`approval|handoff_target|proposal_readability|none`

低证据条目不得使用 `degrade_target=none`。只有高置信、可追溯规则才能进入 `source_business_contract`。

## 约束

- source path 必须来自 `.lgwf/prompt_file_index.json`。
- 不使用“等价自然语言表达”替代固定字段。
- 不修改源目录、目标 package 或文件索引。
- 不生成 proposal、handoff target 或最终 workflow。
