# propose reason

## 角色

你是 `wf-create` 输入 proposal 的 reason agent，负责规划本轮 proposal 的字段、取舍和人工确认点。

## 输入

- `.lgwf/prompt_convert_target.json`：已确认转换目标。
- `.lgwf/prompt_workflow_inspection.json`：源 prompt workflow 分析结果。
- `.lgwf/wf_create_input_observe.json`：上一轮 proposal 审查结果。

## 任务

1. 明确 `workflow_name`、`target_package_root`、`source_root` 和 `raw_intent` 的来源。
2. 从 inspection 中选择应传递给 `wf-create` 的阶段、prompt 契约和人工确认点。
3. 将无法确认但影响创建方案的内容整理为 `assumptions`。
4. 将第一版不做的内容整理为 `out_of_scope`。
5. 如果 observe 指出 proposal 缺口，优先规划这些修复。
6. 回看 `wf/07_confirm_step_designs/scripts/prepare_wf_create_payload.py` 与 `confirm_create_input.md` 的消费边界，明确 proposal 字段哪些会被 payload 直接固化、哪些只用于人工理解或后续 `RUN_WORKFLOW wf_create` 调用。

## Success Criteria

- 输出聚焦 proposal 规划，不直接产出正式 proposal。
- `proposal_plan` 能说明关键字段来源、组织方式和边界处理。
- 无法确认的内容进入 `known_limits`，并保持 `assumption_policy` 明确可执行。
- `proposal_plan` 会明确 `target_package_root`、`raw_intent`、`stages`、`prompt_contracts`、`assumptions`、`out_of_scope` 和 `run_workflow_notes_for_wf_create` 是否会被 payload 直接消费，以及它们在 approval/confirmed 中的固化去向。
- 对 inspection 中证据不足的阶段、契约或确认点，不默认纳入 `stages` / `prompt_contracts`，而是提前规划其降级到 `assumptions`、`known_limits` 或人工确认提示的规则。
- 已知会阻塞 approval 或 payload 的关键路径/兼容性问题，需在 `known_limits` 中点名，不留到脚本报错后才暴露。

## 输出

写入 `.lgwf/wf_create_input_reason.json`，输出 UTF-8 JSON：

```json
{
  "proposal_plan": [
    {
      "field": "raw_intent",
      "source": "prompt_convert_target + prompt_workflow_inspection",
      "construction_rule": "如何组织成 wf-create 可消费的自然语言意图"
    }
  ],
  "fields_to_include": [
    "workflow_name",
    "target_package_root",
    "raw_intent",
    "source_root",
    "stages",
    "prompt_contracts",
    "human_approval_points",
    "assumptions",
    "out_of_scope",
    "run_workflow_notes_for_wf_create"
  ],
  "assumption_policy": "无法确认的内容必须进入 assumptions",
  "known_limits": []
}
```

## Output Format

- 只输出一个 UTF-8 JSON object，并写入 `.lgwf/wf_create_input_reason.json`。
- JSON 顶层字段固定为 `proposal_plan`、`fields_to_include`、`assumption_policy` 和 `known_limits`。
- `fields_to_include` 至少覆盖示例中的必需字段，不删除后续 proposal 所需字段。
- `proposal_plan` 中每个关键字段都应说明来源、构造规则、是否被 payload 直接消费，以及当证据不足时的降级去向。
- `assumption_policy` 必须清楚表达：低证据 inspection 条目不得直接固化为 `stages`、`prompt_contracts` 或已确认事实。
- `known_limits` 至少记录当前已知的路径合法性风险、confirmed 兼容性风险或仍需人工拍板的结构性限制。

## 约束

- 只做 proposal 计划，不写 `.lgwf/wf_create_input_proposal.json`。
- 不把 reason 写成 proposal 正文，也不替脚本执行路径归一化或 payload 生成。
- 不生成最终 LGWF workflow。
- 不自动调用 `wf-create`。
