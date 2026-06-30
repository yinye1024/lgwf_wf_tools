# lgwf-wf-create 工作流指引

本目录已经是 `lgwf-wf-tools/workflows/wf-create` 下的内部 workflow，由 facade 根目录 `registry.json` 派发，不是独立 Codex skill。真实可运行的 workflow package root 固定为 `wf/`，同级 `ws/` 只作为 work-dir，运行状态只允许写入 `ws/.lgwf`。

## 适用场景

- 用户只有原始意图，需要先生成一个 LGWF workflow 初稿。
- 需要把需求方案、业务流转、步骤设计和初稿实现拆成可确认阶段。
- 需要固定第一版结构、路径规则、approval 边界和最小验证入口。

不适用场景：

- 已有 workflow 真实运行失败或卡住，应回到 facade 路由 `wf-fix`。
- 只需要 prompt 基础修复或 prompt 质量升级，应回到 facade 路由 `wf-prompt-fix` 或 `wf-prompt-upgrade`。
- 只需要为已有 workflow 生成 E2E 测试，应回到 facade 路由 `e2e-test-generator`。

## 输入契约

入口允许从原始意图开始，不要求用户先提供完整结构化 JSON。后续阶段会逐步形成：

- `create_requirements_proposal`：需求方案草案。
- `business_flow_proposal`：业务流转草案。
- `step_designs_proposal`：步骤设计草案。
- `implementation_result`：按已确认设计生成的 workflow 初稿说明。

所有目标 package 路径和 resource path 只允许使用包内相对路径，禁止绝对路径、盘符路径和 `..`。

## 状态交接

- `prepare_dsl_reference_context` 复制 facade 内置 bundled client 的 `dsl-assist` 规范到 `.lgwf/create_reference_context/dsl-assist/`，供步骤设计和实现阶段读取。
- `prepare_requirements_confirmation` 读取 `.lgwf/create_requirements_proposal.json`，输出 `requirements_confirmation_context`。
- `prepare_business_flow_confirmation` 读取 `.lgwf/business_flow_proposal.json`，输出 `business_flow_confirmation_context`。
- `prepare_step_design_confirmation` 读取 `.lgwf/step_designs_proposal.json`，输出 `step_design_confirmation_context`。
- `scaffold_package` 优先从 `.lgwf/create_requirements.json` 和 `.lgwf/business_flow.json` 推导脚手架计划，避免依赖人工拼 stdin JSON。

## Approval 边界

- `confirm_requirements` 只确认需求方案；`approve` 后才能写 `.lgwf/create_requirements.json`。
- `confirm_business_flow` 只确认业务流转；`approve` 后才能写 `.lgwf/business_flow.json`。
- `confirm_step_designs` 只确认步骤设计；`approve` 后才能写 `.lgwf/step_designs.json`。
- `revise` 表示局部调整：先进入对应 `revise_*` 人工确认点，由主 agent 根据 `changes` 提交修订后的 `approve` 结果，再固化产物并继续下游。
- `reject` 表示整体不通过，通过 DSL `FAIL_ALL` 终止整个 run，不继续进入下游阶段。
- 当前第一版不自动 approve 任何业务决策，也不接入自动修复链路。

## 固定产物

- `.lgwf/create_requirements_proposal.json`
- `.lgwf/create_requirements_approval.json`
- `.lgwf/create_requirements.json`
- `.lgwf/business_flow_proposal.json`
- `.lgwf/business_flow_approval.json`
- `.lgwf/business_flow.json`
- `.lgwf/step_designs_proposal.json`
- `.lgwf/step_design_confirmation_record.json`
- `.lgwf/step_designs.json`
- `.lgwf/create_reference_context/dsl-assist/*.md`
- `.lgwf/implementation_result.json`
- `reports/create-workflow/create_result_report.md`

## 范围边界

- 不负责自动调用 `lgwf-wf-prompt-fix`。
- 不负责把生成出的目标 workflow 自动接入 facade 路由、registry 或其他治理链路。
- 不承诺端到端业务 happy path 成功。
- 不做自动修复、自动重试或后续 agent 化。
- 创建或修改 `workflow.lgwf` 时必须遵守 `dsl-assist`：根 workflow 保持薄编排，阶段细节优先拆到子 workflow，所有引用路径保持包内相对路径。

## 最小验证

```powershell
python -m unittest discover plugins\team-skills\skills\lgwf-wf-tools\workflows\wf-create\tests
```
