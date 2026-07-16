# wf-create-fast workflow root

本目录是 `wf-create-fast` 的真实 LGWF workflow root。根 `workflow.lgwf` 只做薄编排，阶段细节分别放在：

- `01_confirm_requirements/`
- `02_confirm_business_flow/`
- `03_materialize_scaffold/`
- `04_main_agent_handoff/`

本 workflow 的结束点是 `04_main_agent_handoff` 发布 `next_action=main_agent_authoring` 的 runtime `HANDOFF`。主 agent 先用 `handoff submit` ack，再读取 `.lgwf/main_agent_authoring_handoff.json` 继续当前 authoring；本 workflow 不生成 `step_designs.json`，不执行 implementation units，也不自动启动 `wf-post-fix`。
