# confirm_business_flow

## 职责

确认 `wf-create` 的业务流转结构，并在业务流确认后生成确定性脚手架计划。父级 workflow 只负责编排子流程，不承载具体 prompt、review 或脚本逻辑。

## 输入

- `.lgwf/create_requirements.json`
- `.lgwf/create_requirements_proposal.json`
- `state.lgwf_wf_create.creation_context_dirs`
- `state.lgwf_wf_create.creation_context_files`

## 输出

- `state.lgwf_wf_create.business_flow`
- `state.lgwf_wf_create.scaffold_package_result`

## 子流程

- `01_business_flow_proposal`：通过单个 Codex 节点生成业务流 proposal。
- `02_business_flow_review`：处理人工确认、修订和正式业务流固化。
- `03_scaffold_package`：把已确认需求和业务流转转换成脚手架计划。

## 产物

- `.lgwf/business_flow_proposal.json`
- `.lgwf/business_flow_approval.json`
- `.lgwf/business_flow.json`
- `.lgwf/scaffold_package_result.json`

## 验证

- `python -m unittest tests.test_workflow_integrity`
- `python -m unittest tests.test_artifact_io_contracts`
- `python -m unittest tests.test_scaffold_package_rules`

## 禁止事项

- 不在父级 `workflow.lgwf` 中直接放置 CODEX、PY 或 REVIEW 节点。
- 不绕过 `02_business_flow_review` 直接写 `.lgwf/business_flow.json`。
- 不把脚手架模板、确认 prompt 或阶段私有脚本放回父级目录。
- 不向目标 package 根目录写入 `.lgwf`、`.tmp` 或运行状态文件。
