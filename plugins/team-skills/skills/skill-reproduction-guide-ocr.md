# lgwf-plan skill 复现说明

本文面向另一个 Codex，用于从当前 `lgwf-plan` 目录复现同等能力的 skill。
复现目标不是复制某次 `.tmp` 运行结果，而是复现工作流模板、产物契约、阶段路由和主智能体协作边界。

## 目的

`lgwf-plan` 是一个通用计划驱动任务工作流，用于处理需要先拆计划、再确认验收、最后按验收闭环执行的任务。

它解决的问题是：主智能体不直接拍脑袋写计划或验收标准，而是把原始任务交给独立 Codex ReAct 节点生成计划草案和验收草案；
用户一次性确认后，`task_id` 对齐的计划与验收后，工作流才允许进入实施；
实施完成后再由独立 observe 节点按已确认验收方案评审，并根据结果继续修复、进入下一个任务或请求用户决策。

## 业务角色

- 主智能体：只负责补齐任务输入、向用户展示草案、提交用户确认结果、按工作流继续执行；不得替代独立 Codex 生成计划或验收方案。
- 规划 Codex：读取原始请求和目标文件，生成 `.lgwf/react_task_plan_reason.md` 与 `.lgwf/react_task_plan_proposal.json`。
- 验收 Codex：基于计划草案生成 `.lgwf/react_acceptance_reason.md` 与 `.lgwf/react_acceptance_proposal.json`。
- 实施 Codex：按已确认的 task 上下文实施修改，并写 `.lgwf/react_task_input.json` 作为证据包。
- 评审 Codex：只按已确认 acceptance observe，写 `.lgwf/react_task_result.json`，不得加入新需求。
- 用户：确认任务输入、确认计划与验收合同，并在生成失败或最大尝试次数用尽时选择方向。

## 顶层流程

根工作流 `workflow.lgwf` 的入口是 `generate_plan`，只编排四个业务阶段：

1. `generate_plan`：收集原始任务请求，校验分析目标，通过 ReAct 生成计划草案并自审。
2. `generate_acceptance`：基于计划草案，通过 ReAct 生成验收草案并自审。
3. `confirm_plan_and_acceptance` / `apply_confirmed_contracts`：按 task 对齐展示计划和验收，用户 approve 后写正式契约。
4. `execute_react_loop`：逐 task 实施、observe、记录、路由，直到全部 task 通过或跳过。

根工作流只把 `generate_plan`、`generate_acceptance`、`execute_react_loop` 做成直接子 workflow。
中间确认和落盘只有一次人工确认加一个脚本，因此直接声明在根 `workflow.lgwf` 中。

## 阶段 01：生成计划草案

文件入口：`01_generate_plan/workflow.lgwf`

业务逻辑：

1. `collect_react_task_request` 是 `APPROVAL` 节点。主智能体必须读取 `00_collect_react_task_request/main_agent_request_template.md`，按模板提交用户确认后的任务输入。
2. 任务输入持久化到 `.lgwf/react_task_request.json`。必须包含：
   - `objective`
   - `request`
   - `constraints`
   - 并至少提供 `analysis_target_files` 或 `analysis_target_dirs`。
   具体文件目标必须写进 `analysis_target_files`。
3. `validate_plan_analysis_targets.py` 校验目标是否足够供 Codex 分析，校验通过路由到 `generate_plan_proposal`，否则进入用户方向确认。
4. `generate_plan_proposal` 是 `REACT MAX 3`。
   `reason` 写计划推理，`act` 写计划草案，`observe` 自审计划是否具体可确认，
   `decide.py` 根据文件和 observe 结果决定继续修订或退出 ReAct。
5. `route_plan_generation.py` 判断是否可进入下一阶段；
   如果缺草案、observe 未通过或契约无效，则进入 `confirm_plan_generation_failure_direction`。

关键产物：

- `.lgwf/react_task_request.json`
- `.lgwf/react_task_plan_reason.md`
- `.lgwf/react_task_plan_proposal.json`
- `.lgwf/react_task_plan_observe.json`
- `.lgwf/react_task_plan_generation_direction.json`
计划草案最低要求：

- 顶层有非空 `tasks`。
- 每个 task 必须有 `task_id`、`title`、`objective`、`scope`、`implementation_plan`。
- `implementation_plan` 不能过短或泛化为“检查并修复问题”。
- 推荐保留结构化字段：`scope_detail`、`evidence_refs`、`implementation_steps`、`acceptance_seed`、`required_checks_hint`、`risk_notes`。

失败方向只允许：

- `retry_generation`
- `adjust_request`
- `stop`

## 阶段 02：生成验收草案

文件入口：`02_generate_acceptance/workflow.lgwf`

业务逻辑：

1. `validate_acceptance_codex_inputs.py` 校验计划草案和计划 observe 结果是否足够生成验收。
2. `generate_acceptance_proposal` 是 `REACT MAX 3`。它读取请求、计划草案和计划 observe，生成与计划逐项对齐的验收草案。
3. `decide.py` 校验验收草案结构、task 对齐关系、结构化字段覆盖情况和 acceptance observe 结果。
4. `route_acceptance_generation.py` 判断是否可进入用户确认；失败时进入 `confirm_acceptance_generation_failure_direction`。

关键产物：

- `.lgwf/react_acceptance_reason.md`
- `.lgwf/react_acceptance_proposal.json`
- `.lgwf/react_acceptance_observe.json`
- `.lgwf/react_acceptance_generation_direction.json`

验收草案最低要求：

- 顶层有非空 `tasks`。
- 每个计划 task 必须有相同 `task_id` 的 acceptance。
- 每个 acceptance 必须有非空 `criteria`、`required_checks`、`review_focus`、`out_of_scope`、`plan_validation_map`。
- 如果计划 task 使用了结构化字段，acceptance 还必须提供 `criteria_details`、`required_checks_details`、`traceability`。
- 如果计划 task 有 `implementation_steps`，`plan_validation_map` 必须用整数 `plan_step_index` 覆盖每个 step，并提供 `plan_step`、`expected_evidence` 和 `validation`。
- 如果计划 task 有 `acceptance_seed`，必须有 `acceptance_seed_coverage`。
- 如果计划 task 有 `required_checks_hint`，必须有 `required_checks_hint_coverage`。

验收 observe 通过条件：

- `verdict` 为 `pass`
- `acceptance_is_executable=true`
- `plan_validation_map_complete=true`
- `ready_for_confirmation=true`
- `issues` 和 `required_changes` 为空

失败方向只允许：
- `retry_acceptance_generation`
- `stop`

## 阶段 03：确认并落地合同

根工作流中的 `confirm_plan_and_acceptance` 是人工确认节点，必须读取
`03_confirm_plan_and_acceptance/00_user_decision_template/plan_acceptance_decision_template.md`。

展示要求：

- 按 `task_id` 把计划和验收放在同一行或同一段。
- 同时展示 `scope/scope_detail`、`implementation_plan/implementation_steps`、`criteria/criteria_details`、`required_checks/required_checks_details`、`traceability`。
- 展示逐 step 的 `plan_validation_map`，尤其是 `plan_step_index`。
- 用户只能回复 `approve` 或 `reject`，具体修改意见。
- 未明确 approve 前，不得创建 `.lgwf/react_task_plan.json` 或 `.lgwf/react_acceptance_plan.json`。

`apply_confirmed_contracts.py` 的职责：

- 读取 `.lgwf/react_task_plan_proposal.json`、`.lgwf/react_acceptance_proposal.json`、`.lgwf/react_task_contract_approval.json`。
- 如果 `approval` 含 `reject/拒绝语义`，直接终止。
- 校验计划和验收的 `task_id` 对齐。
- 调用 `manage_react_task.py` 的 `init_plan` 和 `set_acceptance`，写出正式契约。

正式契约：

- `.lgwf/react_task_plan.json`
- `.lgwf/react_acceptance_plan.json`

## 阶段 04：执行 ReAct 闭环

文件入口：`04_execute_react_loop/workflow.lgwf`

业务逻辑：

1. `prepare_react_task_review.py` 读取正式 plan/acceptance，解析当前未完成 task，生成 `.lgwf/react_task_context.json`。
2. `validate_execute_codex_inputs.py` 校验实施 Codex 所需上下文。
3. `implement_react_task` 是 `REACT MAX 3`。
   `reason` 规划本轮实施，`act` 修改文件并写 `.lgwf/react_task_input.json`，
   `observe` 按 acceptance 写 `.lgwf/react_task_result.json`。
4. `publish_react_task_outputs.py` 发布执行输出摘要。
5. `record_react_task_review.py` 校验结果，更新 task 状态，追加历史，生成报告和路由数据。
6. `route_react_task_review.py` 读取 `.lgwf/react_task_route.json`，把下一步路由给 LGWF。

关键产物：

- `.lgwf/react_task_context.json`
- `.lgwf/react_task_input.json`
- `.lgwf/react_task_implementation_reason.md`
- `.lgwf/react_task_result.json`
- `.lgwf/react_task_history.json`
- `.lgwf/react_task_route.json`
- `reports/react-task/react_task_run_summary.json`
- `reports/react-task/react_task_report.json`
- `.lgwf/react_task_route.json`
- `reports/react-task/react_task_run_summary.json`
- `reports/react-task/react_task_report.json`
- `reports/react-task/react_task_report.md`

执行结果校验：

- `react_task_result.json.verdict` 必须是 `pass` 或 `fail`。
- `pass` 必须有价值。
- `pass=true` 时，`required_follow_up` 必须为空，并且必须有非空 `evidence` 和 `accepted`。
- 如果上下文包含结构化合同，`pass=true` 还必须提供非空 `criteria_results`、`required_check_results`、`plan_validation_results`。
- 如果有 `scope_compliance`，`pass=true` 要求 `within_scope=true` 且 `issues` 为空。
- `pass=false` 时必须有非空 `required_follow_up`，每项包含 `title`、`reason`、`locations`、`suggested_change`、`validation`。

执行路由：

- `continue_repair`：当前 task 未通过且未达到 `max_attempts`，回到 `prepare_react_task_review` 继续修复。
- `move_next_task`：当前 task 通过，存在下一个未完成 task，继续准备下一个 task。
- `all_done`：所有 task 都已 `passed` 或 `skipped`，进入 `finish`。
- `requires_user_approval`：当前 task 失败且达到 `max_attempts`，进入 `confirm_react_task_direction`。

达到最大尝试次数时，主智能体必须展示当前 task、尝试次数、失败验收点和 `required_follow_up`，让用户选择调整方向、继续迭代、接受当前结果、跳过或停止。
该 approval 不是任务完成信号，用户选择后仍要继续当前对话。

## 状态机与 task 状态

`manage_react_task.py` 管理正式计划中的 task 状态。
初始化后 task 状态为 `planned`，设置验收后为 `acceptance_specified`，执行中和评审后由记录脚本更新。

常见状态：

- `planned`
- `acceptance_specified`
- `in_progress`
- `under_review`
- `needs_repair`
- `blocked_for_user`
- `passed`
- `skipped`

task 选择规则：总是选择第一个状态不在 `passed`、`skipped` 的 task。
`current_task_id` 会随状态刷新。

## 目录结构复现清单

复现 skill 时应保留以下结构：


lgwf-plan/
  AGENTS.md
  README.md
  SKILL.md
  workflow.lgwf

01_generate_plan/
  workflow.lgwf
  00_collect_react_task_request/main_agent_request_template.md
  01_validate_plan_analysis_targets/scripts/validate_plan_analysis_targets.py
  02_generate_plan_proposal/agents/{spec,reason,act,observe}.md
  02_generate_plan_proposal/scripts/decide.py
  03_route_plan_generation/scripts/*.py

02_generate_acceptance/
  workflow.lgwf
  00_generate_acceptance_proposal/agents/{spec,reason,act,observe}.md
  00_generate_acceptance_proposal/scripts/decide.py
  00_validate_acceptance_targets/scripts/validate_acceptance_codex_inputs.py
  01_route_acceptance_generation/scripts/*.py

03_confirm_plan_and_acceptance/
  00_user_decision_template/plan_acceptance_decision_template.md
  01_apply_confirmed_contracts/scripts/apply_confirmed_contracts.py

04_execute_react_loop/
  workflow.lgwf
  00_prepare/scripts/{manage_react_task,prepare_react_task_review}.py
  00_validate_execute_targets/scripts/validate_execute_codex_inputs.py
  01_implement_task/agents/{spec,reason,act,observe}.md
  01_implement_task/scripts/decide.py
  02_publish/scripts/publish_react_task_outputs.py
  02_record/scripts/record_react_task_review.py
  03_route/scripts/route_react_task_review.py
  05_finish/scripts/finish_react_task_review.py
  common/json_io.py
  scripts/cleanup_lgwf_plan_runtime.py
  tests/test_structured_contracts.py
```

````md
`.tmp/` 是运行工作区，不是模板源码；复现时不要把 `.tmp` 下的历史运行目录当成 skill 源文件。

## 运行工作区约定

从 `lgwf-plan` 包根目录启动时，work-dir 使用相对路径：

```text
.tmp/<run-name>
````

`<run-name>` 根据任务语义生成短横线名称；冲突时追加 `-2`、`-3`。
不要传入机器绝对路径，也不要写到父级 `lgwf` 包下面的 `.plan-runs/`。

启动新的默认回阶段主流程前，可以清理本包运行态：

```powershell
python scripts/cleanup_lgwf_plan_runtime.py --package-root .
```

清理只用于启动新主流程，不应用于保留刚成功 run 的场景。

```



````md
从 `lgwf-plan` 包根目录启动时，work-dir 使用相对路径：

```text
.tmp/<run-name>
````

`<run-name>` 根据任务语义生成短横线名称；冲突时追加 `-2`、`-3`。
不要传入机器绝对路径，也不要写到父级 `lgwf` 包下面的 `.plan-runs/`。

启动新的默认回阶段主流程前，可以清理本包运行态：

```powershell
python scripts/cleanup_lgwf_plan_runtime.py --package-root .
```

清理只用于启动新主流程，不应用于保留刚成功 run 的场景。

## 复现时不可破坏的设计要点

* 主智能体不得生成计划或验收，只能收集请求、展示草案、提交用户确认和继续执行。
* 计划 observe 通过前不得生成验收；验收 observe 通过前不得进入用户确认。
* 用户统一确认前不得写正式 `plan/acceptance`，也不得修改业务目标文件。
* 验收必须和计划逐项对齐，特别是 `implementation_steps` 与 `plan_validation_map[].plan_step_index`。
* 执行 observe 只按已确认 acceptance 验收，不添加新需求。
* `pass=false` 是下一轮修复输入，不是整体失败。
* 达到 `max_attempts` 后必须进入用户方向确认。
* 所有失败方向都必须显式展示失败分类、缺失或无效产物、最近 Codex 结果摘要和可选方向。
* 结构化字段必须在 `init_plan`、`set_acceptance`、确认模板、execute context、observe result 和测试中贯通保留。

## 最小验收方式

复现后至少运行：

```powershell
python -m unittest llm.team.allen.lgwf.lgwf-plan.tests.test_structured_contracts
```

如果模块路径中的短横线导致 `unittest` 模块名不可用，可直接运行文件：

```powershell
python llm\team\allen\lgwf\lgwf-plan\tests\test_structured_contracts.py
```

该测试覆盖：

* `init_plan` 保留结构化计划字段。
* 结构化计划要求验收 `plan_validation_map` 覆盖 `plan_step_index`。
* 结构化上下文中 `pass=true` 不能缺少证据明细。
* 三个 ReAct `decide.py` 都输出顶层 `next`，供运行时路由使用。
* 确认模板必须展示结构化字段。

```

```
