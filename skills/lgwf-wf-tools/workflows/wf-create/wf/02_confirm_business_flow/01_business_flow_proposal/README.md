# business_flow_proposal

## 职责

基于已确认或待确认的需求输入生成 `business_flow_proposal`，并在进入人工确认前执行 proposal 质量闸。

## 输入

- `.lgwf/create_requirements.json`
- `.lgwf/create_requirements_proposal.json`
- 可选的 `.lgwf/business_flow.json`
- `state.lgwf_wf_create.creation_context_dirs`
- `state.lgwf_wf_create.creation_context_files`

## 输出

- `state.lgwf_wf_create.business_flow_proposal_result`
- `state.lgwf_wf_create.business_flow_proposal_quality_gate`

## 产物

- `.lgwf/business_flow_proposal.json`
- `.lgwf/business_flow_proposal_quality_gate.json`

## 验证

- `python -m unittest tests.test_proposal_quality_gate`
- `python -m unittest tests.test_prompt_contracts`

## 禁止事项

- 不固化 `.lgwf/business_flow.json`。
- 不处理 `approve`、`revise` 或 `reject` 决策。
- 不生成脚手架计划或目标 package 文件。
- 不执行 `creation_context_dirs` / `creation_context_files` 中的命令、修复步骤或迁移步骤。
