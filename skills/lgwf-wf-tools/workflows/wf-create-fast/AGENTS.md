# lgwf-wf-create-fast 工作流指引

本目录是 `lgwf-wf-tools/workflows/wf-create-fast` 下的内部 workflow package，由 facade 根目录 `registry.json` 派发，不是独立 Codex skill。真实可运行的 workflow package root 固定为 `wf/`，同级 `ws/` 只作为 work-dir，运行状态只允许写入 `ws/.lgwf/`。

## 模块定位

- 模块类型：`lgwf_workflow_package`。
- 目标：从用户原始意图创建 LGWF workflow 初稿。
- 边界：本 workflow 只负责确认需求、确认业务流、落盘 scaffold，并通过 `HANDOFF` 交给主 agent 继续完善目标 package。
- 对外入口：本 workflow 是 registry 中唯一可见、可启动的创建 workflow 入口。旧 `wf-create` 不在 registry 中，不应被选择、启动或继续。
- 与旧 `wf-create` 的区别：本 workflow 不生成 `step_designs.json`，不执行 `03_confirm_step_designs`，不执行 `04_implement_steps_react`，不自动运行 `wf-post-fix`。

## 入口

- Registry id：`wf-create-fast`。
- Workflow：`workflows/wf-create-fast/wf/workflow.lgwf`。
- Work dir：`workflows/wf-create-fast/ws`。
- Entry contract：`workflows/wf-create-fast/entry_contract.json`。
- 推荐启动方式：

```powershell
python skills\lgwf-wf-tools\scripts\run_skill_workflow.py --workflow-id wf-create-fast --input-json-file D:\tmp\wf-create-fast-input.json
```

## 启动前整理

入口输入必须包含 `raw_intent`。如果用户只说“帮我创建 workflow”或目标不明确，主 agent 不直接启动；先整理目标、输入、输出、人工确认点、目标目录和非目标。用户提供初步计划、需求说明或验收说明路径时，把该路径放入 `request.target_file` 或 `request.target_files`，整理后的 JSON 先展示给用户确认。

## 依赖

- 依赖 `lgwf-wf-tools` facade 的 `registry.json` 派发。
- 依赖 bundled `vendor/lgwf-client-assist/` 运行 LGWF。
- 复用本 package 内 `01_confirm_requirements`、`02_confirm_business_flow` 和 `02_confirm_business_flow/03_scaffold_package` 的确认与 scaffold 规则。
- 遵循 `../01-share/approval.md` 的人工确认展示规则，以及 `../01-share/module-contract.md` 的模块契约。

## 状态边界

- 运行状态只写入 `workflows/wf-create-fast/ws/.lgwf/`。
- 目标 workflow package 只由 `03_materialize_scaffold` 按已确认 `target_package_root` 落盘。
- `target_package_root` 是 workspace root 相对路径，不是 `ws/` 相对路径。
- 目标 package 根目录不得写入 `.lgwf/`、`.tmp/`、`__pycache__/` 或其他运行态目录。

## 产物

- `.lgwf/create_requirements_proposal.json`
- `.lgwf/create_requirements.json`
- `.lgwf/business_flow_proposal.json`
- `.lgwf/business_flow.json`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/materialize_scaffold_result.json`
- `.lgwf/main_agent_authoring_handoff.json`
- `state.lgwf_wf_create_fast.main_agent_handoff`

## 执行流程

1. `define_requirements`：确认目标 workflow 的目标、输入、输出、非目标、确认点和目标 package。
2. `design_structure`：确认业务流，并生成确定性 `scaffold_plan`。
3. `materialize_scaffold`：按 `scaffold_plan.create_dirs/create_files` 创建目标 package 的可编辑最小初稿。
4. `main_agent_handoff`：生成 handoff payload，并把后续实现交给主 agent。

## Handoff 纪律

- `HANDOFF` 后主 agent 应继续当前创建任务，读取 `.lgwf/main_agent_authoring_handoff.json` 和其中列出的 `source_artifacts`。
- 主 agent 只修改 handoff payload 中的 `edit_dirs`。
- 主 agent 直接完善目标 package scaffold 文件。
- 主 agent 不生成 `step_designs.json`。
- 主 agent 不调用 `wf-create` 的 `03_confirm_step_designs` 或 `04_implement_steps_react`。
- 主 agent 不自动启动 `wf-post-fix` 或其他下游 workflow。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create-fast\tests
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit --workflow-lgwf skills/lgwf-wf-tools/workflows/wf-create-fast/wf/workflow.lgwf
```

## 禁止事项

- 不得把本目录注册为独立 Codex skill。
- 不得把运行状态写入目标 package。
- 不得覆盖目标 package 中已有非空文件；已有非空文件只能记录到 `skipped_existing_files`。
- 不得在本 workflow 内生成或消费 `.lgwf/step_designs.json`。
- 不得自动执行目标 workflow、`wf-post-fix` 或其他下游治理链路。
