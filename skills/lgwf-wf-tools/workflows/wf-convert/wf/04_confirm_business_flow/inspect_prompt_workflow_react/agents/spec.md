# inspect_prompt_workflow_react 规格

## 角色

本 ReAct 把源 prompt workflow 的文件索引和可读内容转换为后续 proposal 可消费的事实基础。

## 输入

- `.lgwf/prompt_file_index.json`
- `.lgwf/prompt_workflow_inspection_observe.json`：上一轮 canonical Observe；第一轮为 `initial`。

## ReAct 分工

- `reason`：根据上一轮 canonical Observe 规划证据提取和阻塞问题修复。
- `act`：输出固定结构的 `.lgwf/prompt_workflow_inspection.json`。
- `observe`：调用本目录的 `observe_quality_gate`，先由 Python 做确定性检查，再由 Codex 做语义检查，最后由 Python 合并。
- `decide`：只根据 canonical Observe 的 `blocking` 决定继续或退出。

## 输出契约

inspection 顶层字段固定为：

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

`detected_stages`、`prompt_contracts` 和业务规则条目必须使用同目录 `act.md` 声明的固定字段，不接受把证据强度、消费方或降级规则藏在自由文本中。

## 约束

- 只分析源 prompt workflow，不修改源目录。
- `source_business_contract` 只包含高置信、可追溯业务规则。
- 执行矩阵、预填充、few-shot、角色强化和格式诱导进入 `prompt_execution_mechanics` 或 `discarded_prompt_techniques`。
- 不生成 proposal、LGWF DSL、目标 package 或 handoff target。
- 不调用其它 workflow。
