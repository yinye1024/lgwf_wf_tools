# propose_create_input_react 规格

## 角色

本 ReAct 把已确认目标、inspection 和 inspection Observe 整理为可人工确认的 `wf-create-fast` handoff target proposal。

## 输入

- `.lgwf/prompt_convert_target.json`
- `.lgwf/prompt_workflow_inspection.json`
- `.lgwf/prompt_workflow_inspection_observe.json`
- `.lgwf/wf_create_fast_input_observe.json`
- `.lgwf/wf_create_fast_input_proposal.json`

## ReAct 分工

- `reason`：规划字段来源，并为上一轮 blocking issues 生成修复计划。
- `act`：输出固定结构 proposal。
- `observe`：调用本目录的 `observe_quality_gate`，执行 Python 确定性检查、Codex 语义检查和 Python 合并。
- `decide`：只根据 canonical Observe 的 `blocking` 决定继续或退出。

## 输出契约

proposal 顶层字段固定为：

```json
{
  "workflow_name": "example-workflow",
  "target_package_root": "skills/example-workflow",
  "raw_intent": "完整创建意图",
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

具体条目结构以同目录 `act.md` 为准。

## 约束

- proposal 面向 `wf-create-fast`，不直接生成最终 workflow。
- `stages` 和 `prompt_contracts` 只接收 inspection 中高置信、可追溯条目。
- inspection 的非阻塞 issues 必须降级或传递，不能丢失。
- 不自动调用 `wf-create-fast` 或修复类 workflow。
