# step_design_review

## 职责

把步骤设计 proposal 转为 REVIEW 确认上下文，处理 `approve`、`revise`、`reject` 决策，并在批准后固化 `.lgwf/step_designs.json` 和准备 `.lgwf/implementation_context.json`。

## 输入

- `.lgwf/step_designs_proposal.json`
- `state.lgwf_wf_create.step_design_confirmation_context`

## 输出

- `state.lgwf_wf_create.step_design_confirmation_context`
- `state.lgwf_wf_create.step_design_revision_context`
- `state.lgwf_wf_create.step_design_revision_result`
- `state.lgwf_wf_create.step_designs`
- `.lgwf/step_design_confirmation_record.json`
- `.lgwf/step_designs.json`
- `.lgwf/implementation_context.json`

## 产物

- `.lgwf/step_design_confirmation_record.json`
- `.lgwf/step_designs_proposal.json`（`revise` 后由 `apply_step_design_revision` 写回）
- `.lgwf/step_designs.json`
- `.lgwf/implementation_context.json`

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

## 禁止事项

- 不重新生成步骤设计 proposal。
- `approve` 不携带业务 value，只固化已经展示并确认的 proposal。
- `revise` 必须携带完整修订 proposal，先写回 `.lgwf/step_designs_proposal.json`，再重入本 REVIEW 子流程。
- `reject` 必须通过 `FAIL_ALL` 终止本分支，不进入实现阶段。
