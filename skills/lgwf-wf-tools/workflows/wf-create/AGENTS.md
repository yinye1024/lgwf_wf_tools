# lgwf-wf-create 工作流指引

本目录已经是 `lgwf-wf-tools/workflows/wf-create` 下的内部 workflow，由 facade 根目录 `registry.json` 派发，不是独立 Codex skill。真实可运行的 workflow package root 固定为 `wf/`，同级 `ws/` 只作为 work-dir，运行状态只允许写入 `ws/.lgwf`。

## 模块契约

- 模块类型：`lgwf_workflow_package`。
- 执行前必须读取 `../01-share/module-contract.md`、`../01-share/registry-contract.md`、`../01-share/lgwf-dispatch.md`、`../01-share/lgwf-monitor.md`、`../01-share/approval.md` 和 `../01-share/artifacts.md`。
- 入口字段、输入示例和 `--auto-human` 策略以本目录 `entry_contract.json` 为准；本文件只解释业务纪律和运行边界。
- 本模块生成的目标 workflow 也必须按 `module-contract.md` 补齐自包含契约。

## 适用场景

- 用户只有原始意图，需要先生成一个 LGWF workflow 初稿。
- 需要把需求方案、业务流转、步骤设计和初稿实现拆成可确认阶段。
- 需要固定第一版结构、路径规则、approval 边界和最小验证入口。

不适用场景：

- 已有 workflow 真实运行失败或卡住，应回到 facade 路由 `wf-fix`。
- 只需要 prompt 基础修复或 prompt 质量升级，应回到 facade 路由 `wf-prompt-fix` 或 `wf-prompt-upgrade`。
- 只需要为已有 workflow 生成 E2E 测试，应回到 facade 路由 `e2e-test-generator`。

## 执行纪律

facade 命中本 workflow 后，必须启动或继续 `wf-create` run；主 agent 不能直接手工创建目标 workflow package、直接写目标 `workflow.lgwf`、直接注册 registry，或用 `apply_patch` 脚手架替代本 workflow 的需求、业务流和步骤设计确认。

如果 `wf-create` 已经启动或继续，但 runtime 或子 Codex 进程出现 stale、异常退出、无产物等可复核问题，主 agent 必须先展示 run id、状态文件或进程证据、已完成阶段、未完成阶段和恢复选项。只有用户明确确认后，才允许人工恢复、停止 run 后转入其他 workflow，或按用户确认的范围补救。

## 输入契约

入口允许从原始意图开始，不要求用户先提供完整结构化 JSON。为了支持 `wf-convert` 的闭环转换，入口也兼容 `source_business_contract`、`conversion_mapping` 和 `prompt_workflow_context` 等结构化上下文；这些字段存在时优先作为需求和业务流设计依据，缺失时保持只消费 `raw_intent` 的旧行为。后续阶段会逐步形成：

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
- `validate_created_package` 在实现阶段之后确定性校验目标 package：目标目录必须存在，`wf/workflow.lgwf` 必须存在，已批准 stage 必须有 `wf/<stage>/workflow.lgwf` 以及 `agents/`、`scripts/`、`resources/`，且 `lgwf.py audit` 必须通过；失败时终止，不进入 summary 或 handoff。
- `prepare_post_fix_handoff` 优先读取 `state.lgwf_wf_create.summary_result`，当父 workflow 未把 summary 正确传入 stdin 时，回退读取 `.lgwf/create_result_summary.json`，生成 `wf-post-fix` 的 handoff payload 和 `.lgwf/post_fix_handoff_input.json`。
- `handoff_wf_post_fix` 是结束节点，只暴露 `wf-post-fix` pending action 给主 agent；不得自动启动下游 workflow，必须等待用户确认。

## Approval 边界

- `confirm_requirements` 只确认需求方案；`approve` 后才能写 `.lgwf/create_requirements.json`。
- `confirm_business_flow` 只确认业务流转；`approve` 后才能写 `.lgwf/business_flow.json`。
- `confirm_step_designs` 只确认步骤设计；`approve` 后才能写 `.lgwf/step_designs.json`。
- 当前确认节点以 `approve` 和 `reject` 驱动运行分支；若人工 review 记录出现 `revise` 反馈，只作为控制面反馈留存，不直接生成 confirmed 业务结构。
- `approve` 后由固定 proposal 文件固化 confirmed artifact，禁止把 human decision record 当作业务对象写入 `confirmed`。
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
- `.lgwf/created_package_validation.json`
- `.lgwf/post_fix_handoff_input.json`
- `reports/create-workflow/create_result_report.md`

## 范围边界

- 不负责自动调用 `lgwf-wf-prompt-fix`。
- 结束时只通过 `HANDOFF` 引导用户选择是否运行 `wf-post-fix`，不自动执行。
- 不负责把生成出的目标 workflow 自动接入 facade 路由、registry 或其他治理链路。
- 不承诺端到端业务 happy path 成功。
- 不做自动修复、自动重试或后续 agent 化。
- 创建或修改 `workflow.lgwf` 时必须遵守 `dsl-assist`：根 workflow 保持薄编排，阶段细节优先拆到子 workflow，所有引用路径保持包内相对路径。

## 最小验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```
