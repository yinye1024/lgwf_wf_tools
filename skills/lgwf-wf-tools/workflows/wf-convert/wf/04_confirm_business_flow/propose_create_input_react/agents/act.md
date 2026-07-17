# Act slot：生成创建输入 proposal

## 角色

你负责把目标信息、inspection、inspection Observe 和 reason 计划合成为可人工确认的固定结构 proposal。

## 输入

- `.lgwf/prompt_convert_target.json`
- `.lgwf/prompt_workflow_inspection.json`
- `.lgwf/prompt_workflow_inspection_observe.json`
- `.lgwf/wf_create_fast_input_reason.json`
- `.lgwf/wf_create_fast_input_proposal.json`

## 顶层输出

只输出 UTF-8 JSON object，顶层字段固定为：

```json
{
  "workflow_name": "example-workflow",
  "target_package_root": "skills/example-workflow",
  "raw_intent": "基于现有 prompt workflow 创建 LGWF workflow：...",
  "source_root": "skills/example-prompt-workflow",
  "stages": [],
  "prompt_contracts": [],
  "source_business_contract": {},
  "prompt_execution_mechanics": [],
  "presentation_constraints": [],
  "discarded_prompt_techniques": [],
  "conversion_mapping": [],
  "parity_requirements": [],
  "human_approval_points": [],
  "assumptions": [],
  "out_of_scope": [],
  "run_workflow_notes_for_wf_create_fast": []
}
```

## 固定条目契约

`stages` 必须保留 inspection 的 `stage_id` 和证据：

```json
{
  "stage_id": "collect_input",
  "name": "收集输入",
  "responsibility": "阶段职责",
  "inputs": [],
  "outputs": [],
  "source_files": ["README.md"],
  "evidence_strength": "high",
  "evidence_summary": "支持该阶段的来源摘要"
}
```

`prompt_contracts`：

```json
{
  "prompt_path": "agents/example.md",
  "responsibility": "应保留职责",
  "inputs": [],
  "outputs": [],
  "constraints": [],
  "source_files": ["agents/example.md"],
  "evidence_strength": "high",
  "evidence_summary": "支持该契约的来源摘要"
}
```

`conversion_mapping`：

```json
{
  "mapping_id": "mapping_001",
  "source_rule_ids": ["decision_rule_001"],
  "mapping_type": "convert_to_lgwf_node",
  "target_design": "目标 LGWF 节点或约束",
  "rationale": "为什么这样映射"
}
```

`mapping_type` 只能是：

- `preserve_business_logic`
- `convert_to_lgwf_node`
- `convert_to_script`
- `convert_to_schema_constraint`
- `discard_prompt_technique`
- `manual_confirmation_required`

`parity_requirements`：

```json
{
  "requirement_id": "parity_001",
  "source_rule_ids": ["decision_rule_001"],
  "description": "必须保持的业务一致性",
  "verification": "后续如何验证"
}
```

## 生成规则

- `raw_intent` 独立覆盖目标、阶段、输入、输出、人工确认点和首版非目标。
- stages、prompt contracts 只复制 inspection 中 `evidence_strength=high` 的可追溯条目。
- `source_business_contract` 保留原 `rule_id`，不得重编号或丢失来源。
- 每个业务规则都必须被 `conversion_mapping` 和 `parity_requirements` 引用。
- inspection 的非阻塞 issues 必须进入 assumptions、notes 或人工确认点。
- `out_of_scope` 至少说明不直接生成最终 package、不跳过人工确认、不自动调用其它 workflow。
- `target_package_root` 不得为空、`.`、URL、包含 `..` 或 `.lgwf`。
- blocking issue 无法从证据中确认时，应降级而不是伪造事实。

## 约束

- 不修改源 prompt workflow。
- 不使用自由文本替代固定证据和引用字段。
- 不写 confirmed 文件或 handoff target。
- 不自动调用 `wf-create-fast`。
