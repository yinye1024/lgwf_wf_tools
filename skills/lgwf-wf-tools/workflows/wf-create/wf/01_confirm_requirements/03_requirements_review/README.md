# requirements_review

## 职责

把需求 proposal 转成 REVIEW 确认上下文，处理 `approve`、`revise`、`reject` 决策，并在 approve 后固化正式需求契约。

## 输入

- `.lgwf/create_requirements_proposal.json`
- `.lgwf/create_requirements_proposal_quality_gate.json`
- `state.lgwf_wf_create.requirements_confirmation_context`

## 输出

- `state.lgwf_wf_create.requirements_confirmation_context`
- `state.lgwf_wf_create.requirements_revision_context`
- `state.lgwf_wf_create.create_requirements`

## 产物

- `.lgwf/create_requirements_approval.json`
- `.lgwf/create_requirements_revision_approval.json`
- `.lgwf/create_requirements.json`

## 验证

- `python -m unittest tests.test_artifact_io_contracts`
- `python -m unittest tests.test_structured_contracts`

## 禁止事项

- 不重新生成需求 proposal。
- `approve` 不携带业务 value，只固化已经展示并确认的 proposal。
- `revise` 只重入本 REVIEW 子流程，不绕过人工确认直接写 confirmed artifact。
