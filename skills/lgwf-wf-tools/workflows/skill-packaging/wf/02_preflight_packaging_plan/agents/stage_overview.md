# preflight-packaging-plan

## Role
你是预检阶段说明文档，负责说明本阶段如何在真实写入前完成结构校验、风险显式化和计划草案生成。

## Inputs
- `.lgwf/packaging_request.json`
- `.lgwf/packaging_write_scope.json`
- `resources/packaging_plan_template.json`
- `wf/shared/scripts/packaging_common.py`

## Task
1. 校验源 skill 结构。
2. 校验 runtime 来源是否完整。
3. 检查输出目录状态与覆盖风险。
4. 生成结构化 `packaging_plan_proposal`。

## Output
本阶段输出 `.lgwf/packaging_preflight.json` 和 `.lgwf/packaging_plan_proposal.json`。
