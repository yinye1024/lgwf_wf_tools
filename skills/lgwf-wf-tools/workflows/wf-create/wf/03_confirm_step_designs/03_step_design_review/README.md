# step_design_review

## 职责

把已通过 structural gate 的步骤设计 proposal 自动固化为 `.lgwf/step_designs.json`，并准备 `.lgwf/implementation_context.json`。本子流程不再提供人工 `approve` / `revise` / `reject` REVIEW。

## 输入

- `.lgwf/step_designs_proposal.json`
- `.lgwf/step_design_observation.json`

## 输出

- `state.lgwf_wf_create.step_designs`
- `.lgwf/step_designs.json`
- `.lgwf/implementation_context.json`

## 产物

- `.lgwf/step_designs_proposal.json`
- `.lgwf/step_designs.json`
- `.lgwf/implementation_context.json`

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

## 禁止事项

- 不重新生成步骤设计 proposal。
- 不接受人工 revise；步骤设计问题必须回到 `02_step_design_proposal` 的 structural gate / repair ReAct 修复。
- 不在 `.lgwf/step_design_observation.json.passed` 为 `true` 且 `proposal_hash` 匹配当前 proposal 前写入 `.lgwf/step_designs.json`。
