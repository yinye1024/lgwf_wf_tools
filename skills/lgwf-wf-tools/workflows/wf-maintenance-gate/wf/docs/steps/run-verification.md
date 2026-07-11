# run-verification

## step_slug

`run-verification`

## step_name

执行确认后的验证

## goal

设计 `wf/05_run_verification/workflow.lgwf`，按已确认计划顺序执行健康检查、workflow tests、可选 deep doctor、可选 pre-release 和可选 package smoke，并把结果统一固化为 `.lgwf/verification_results.json` 与 `.lgwf/failure_routes.json`。本阶段的核心要求是“记录事实但不自动修复”，把失败、超时、跳过和写入结果都结构化暴露出来，为总结阶段提供可靠输入。

## inputs

- 上游阶段或节点：
  - `confirm-verification-plan`
  - `.lgwf/business_flow.json` 中 `05_run_verification` 阶段定义
- 依赖文件或状态：
  - `.lgwf/verification_plan.json`
  - `wf/shared/scripts/maintenance_gate_common.py`
  - `docs_tmp/wf-maintenance-gate-development.md`
  - `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`
- 关键约束：
  - 只执行已经确认的命令
  - 失败要记录，但不能自动修复
  - package smoke 只能在已确认且路径安全时执行
  - 写入型命令的落盘范围必须与 plan 中声明一致

## outputs

- 预期生成的文件：
  - `wf/05_run_verification/workflow.lgwf`
  - `wf/05_run_verification/scripts/*.py`
  - `wf/05_run_verification/resources/*`
  - `.lgwf/verification_results.json`
  - `.lgwf/failure_routes.json`
- 预期生成的目录：
  - `wf/05_run_verification/agents/`
  - `wf/05_run_verification/scripts/`
  - `wf/05_run_verification/resources/`
- 交付给下游的结构片段：
  - 每条命令的 return code、stdout 摘要、stderr 摘要、超时状态、耗时和关键产物路径
  - 失败项到 `wf-fix`、`wf-prompt-fix`、`wf-prompt-upgrade`、`wf-dsl-upgrade`、`e2e-test-generator`、`self-improve` 等路由建议
  - 对 zip smoke、deep doctor 和 pre-release 的跳过原因

## dependencies

- 前置步骤：
  - `define-shared-helper-and-tests`
  - `confirm-verification-plan`
- 依赖节点：
  - 已确认计划中的 commands、write_effects、timeout 和 short-circuit 规则
- 需要人工确认的位置：
  - 当前阶段不再新增人工确认；只消费上一个阶段已经确认的计划

## implementation_suggestions

- 用确定性 runner 脚本顺序执行命令，统一捕获 return code、stdout/stderr 摘要、开始结束时间、超时状态和关键 JSON/报告路径。
- 对允许继续的失败项继续记录后续命令结果；对标记 short-circuit 的高风险失败应按计划提前停止，并把提前停止原因写入结果。
- package smoke 执行前要再次校验输出 zip 目标是否符合已确认路径和覆盖策略，不能在脚本里偷偷改路径或清空目标目录。
- `failure_routes.json` 不负责修复，只给出“失败类型 -> 建议 workflow”映射及其原因，例如 DSL audit 问题建议 `wf-dsl-upgrade` 或 `wf-fix`，prompt/契约问题建议 `wf-prompt-fix`。
- 资源目录可放命令执行结果 schema、stdout/stderr 摘要模板和失败路由映射表，减少脚本中的硬编码。

## 修订补充：执行结果 schema 与失败路由

`verification_results.json` 必须记录完整事实，而不是只记录通过/失败：

```json
{
  "commands": [
    {
      "check_id": "doctor_basic",
      "status": "pass",
      "command": ["python", "scripts/doctor_lgwf_wf_tools.py"],
      "cwd": "skills/lgwf-wf-tools",
      "return_code": 0,
      "duration_ms": 1200,
      "timed_out": false,
      "stdout_summary": "doctor completed",
      "stderr_summary": "",
      "artifact_paths": [],
      "write_effects_observed": [],
      "failure_type": null,
      "short_circuit_triggered": false
    }
  ],
  "skipped": [
    {
      "check_id": "pre_release",
      "reason": "allow_pre_release=false"
    }
  ],
  "stopped_early": false,
  "stop_reason": null
}
```

stdout/stderr 摘要规则：

- 保存前后若干关键行或脚本输出中的 summary 字段，不把完整长日志塞进 JSON。
- 若命令超时，`timed_out=true`、`return_code=null`，`failure_type="timeout"`。
- 若命令不存在或 cwd 不安全，命令不得执行，结果记为 `status="fail"` 和 `failure_type="command_contract"`。

`failure_routes.json` 的最小映射：

| failure_type | 建议 route | reason |
| --- | --- | --- |
| `dsl_audit`、`workflow_compile` | `wf-dsl-upgrade` 或 `wf-fix` | DSL 结构或运行拓扑失败 |
| `prompt_contract` | `wf-prompt-fix` | prompt 输入输出或审核规则不满足 |
| `prompt_quality` | `wf-prompt-upgrade` | prompt 可维护性或质量需要升级 |
| `entry_contract`、`registry`、`artifact_contract` | `wf-fix` | package 契约、registry 或 artifact 声明不一致 |
| `missing_tests`、`test_failure` | `e2e-test-generator` 或 `wf-fix` | 测试缺失或失败 |
| `self_improve_health`、`pre_release` | `self-improve` | 发布前治理或自评失败 |
| `packaging`、`zip_conflict` | `skill-packaging` 或手工确认输出策略 | 打包或输出 zip 策略失败 |
| `timeout`、`command_contract` | `needs_review` | 命令自身不可判定或执行环境异常 |

运行阶段必须只消费 `.lgwf/verification_plan.json` 中的命令。若发现实际命令要写入未声明目录，应停止该命令并记录 `failure_type="command_contract"`。

## acceptance_notes

- 重点确认运行阶段不发明新命令，只执行 `.lgwf/verification_plan.json` 中已批准的集合。
- 重点确认 stdout/stderr 记录是摘要而不是整段原文转储，避免把运行日志当成业务 artifact。
- 重点确认失败路由只是建议，不会在当前 workflow 内自动跳转、自动修复或自动重试。
- 重点确认 zip smoke 的覆盖风险、deep doctor 的写入目录和 pre-release 的耗时都以计划中的声明为准，没有额外副作用。

## out_of_scope

- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 自动提交 git、自动发布 zip 或自动执行下游 workflow
