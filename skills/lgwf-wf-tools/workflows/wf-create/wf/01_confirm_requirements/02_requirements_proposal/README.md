# requirements_proposal

## 职责

基于已确认的 raw intent 和只读创建资料生成需求 proposal，并在进入人工确认前执行质量闸。

## 输入

- `.lgwf/raw_intent_request.json`
- `state.lgwf_wf_create.creation_context_dirs`
- `state.lgwf_wf_create.creation_context_files`
- 可选的只读创建资料目录或文件。

## 输出

- `state.lgwf_wf_create.requirements_proposal_result`
- `state.lgwf_wf_create.create_requirements_proposal_quality_gate`

## 产物

- `.lgwf/create_requirements_proposal.json`
- `.lgwf/create_requirements_proposal_quality_gate.json`

## 验证

- `python -m unittest tests.test_proposal_quality_gate`
- `python -m unittest tests.test_prompt_contracts`

## 禁止事项

- 不固化 `.lgwf/create_requirements.json`。
- 不处理需求 review、revise 或 approve 决策。
- 不读取本子流程输入契约以外的目标 package、历史 run 或宿主仓库样例。
