# observe_step_designs

## 职责

本 slot workflow 先运行确定性 structural gate，再由 Codex 做 semantic audit，最后合并为正式 `.lgwf/step_design_observation.json`。

## 输入

- `.lgwf/step_design_reason.json`
- `.lgwf/step_designs_proposal.json`
- `.lgwf/create_requirements.json`
- `.lgwf/business_flow.json`
- `.lgwf/scaffold_package_result.json`

## 输出

- `.lgwf/step_design_structural_gate.json`
- `.lgwf/step_design_semantic_observation.json`
- `.lgwf/step_design_observation.json`
- `.lgwf/step_designs_proposal_quality_gate.json`

## 产物

`.lgwf/step_design_observation.json` 是下一轮 REASON 的唯一正式反馈契约；`.lgwf/step_designs_proposal_quality_gate.json` 保留为最终 assert 的兼容入口。

## 验证

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create\tests\test_proposal_quality_gate.py
```

## 禁止事项

- 不修改 proposal。
- 不写 `.lgwf/step_designs.json`。
- 不让 Codex 覆盖确定性 structural gate 的失败结果。
