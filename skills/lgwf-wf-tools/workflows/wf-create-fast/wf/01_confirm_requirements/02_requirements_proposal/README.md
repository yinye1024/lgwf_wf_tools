# requirements_proposal

## 职责

基于已确认的 raw intent 和只读创建资料，用一个小型 ReAct 循环生成并修复需求 proposal；质量闸通过后才进入人工确认。

## 输入

- `.lgwf/raw_intent_request.json`
- `state.lgwf_wf_create_fast.creation_context_dirs`
- `state.lgwf_wf_create_fast.creation_context_files`
- 可选的只读创建资料目录或文件。

## 输出

- `state.lgwf_wf_create_fast.requirements_proposal_result`
- `state.lgwf_wf_create_fast.create_requirements_proposal_quality_gate`

## 产物

- `.lgwf/create_requirements_proposal.json`
- `.lgwf/create_requirements_proposal_quality_gate.json`，第一轮为空对象表示无上一轮反馈，随后由 OBSERVE 阶段真实校验覆盖。
- `.lgwf/create_requirements_proposal_react_context.json`
- `.lgwf/create_requirements_proposal_decision.json`

## 验证

- `python -m unittest tests.test_proposal_quality_gate`
- `python -m unittest tests.test_prompt_contracts`

## 禁止事项

- 不固化 `.lgwf/create_requirements.json`。
- 不处理需求 review、revise 或 approve 决策。
- 不读取本子流程输入契约以外的目标 package、历史 run 或宿主仓库样例。
- ReAct 达到最大轮次仍未通过质量闸时，不进入 `requirements_review`。
