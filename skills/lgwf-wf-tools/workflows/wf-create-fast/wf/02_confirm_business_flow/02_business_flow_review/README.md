# business_flow_review

## 职责

把业务流 proposal 转成 REVIEW 确认上下文，处理 `approve`、`revise`、`reject` 决策，并在 approve 后固化正式业务流转契约。

## 输入

- `.lgwf/business_flow_proposal.json`
- `state.lgwf_wf_create_fast.business_flow_confirmation_context`

## 输出

- `state.lgwf_wf_create_fast.business_flow_confirmation_context`
- `state.lgwf_wf_create_fast.business_flow_revision_context`
- `state.lgwf_wf_create_fast.business_flow_revision_result`
- `state.lgwf_wf_create_fast.business_flow`

## 产物

- `.lgwf/business_flow_approval.json`
- `.lgwf/business_flow_proposal.json`（`revise` 后由 `apply_business_flow_revision` 写回）
- `.lgwf/business_flow.json`

## 验证

- `python -m unittest tests.test_artifact_io_contracts`
- `python -m unittest tests.test_state_handoff_contracts`

## 禁止事项

- 不重新生成业务流 proposal。
- `approve` 不携带业务 value，只固化已经展示并确认的 proposal。
- `revise` 必须携带完整修订 proposal，先写回 `.lgwf/business_flow_proposal.json`，再重入本 REVIEW 子流程。
