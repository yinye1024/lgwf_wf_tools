# plan-verification

## step_slug

`plan-verification`

## step_name

生成验证计划草案

## goal

设计 `wf/03_plan_verification/workflow.lgwf`，根据影响分类、维护意图和验证等级生成待确认的 `verification_plan_proposal.json`。该阶段要把“推荐做哪些检查”进一步落成可执行的命令集合、timeout、写入影响、跳过条件和预估范围，让后续 REVIEW 看到的是完整执行计划而不是口头建议。

## inputs

- 上游阶段或节点：
  - `classify-impact`
  - `.lgwf/business_flow.json` 中 `03_plan_verification` 阶段定义
- 依赖文件或状态：
  - `.lgwf/change_context.json`
  - `.lgwf/impact_classification.json`
  - `docs_tmp/wf-maintenance-gate-development.md`
  - `wf/shared/scripts/maintenance_gate_common.py`
  - `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`
- 关键约束：
  - 计划只生成 proposal，不直接执行命令
  - `allow_deep_doctor`、`allow_workflow_tests`、`allow_pre_release`、`allow_package_smoke` 必须严格控制可选命令是否进入计划
  - 每个命令都要带 `cwd`、`timeout`、`write_effects`、`can_skip` 或等价字段

## outputs

- 预期生成的文件：
  - `wf/03_plan_verification/workflow.lgwf`
  - `wf/03_plan_verification/scripts/*.py`
  - `wf/03_plan_verification/resources/*`
  - `.lgwf/verification_plan_proposal.json`
- 预期生成的目录：
  - `wf/03_plan_verification/agents/`
  - `wf/03_plan_verification/scripts/`
  - `wf/03_plan_verification/resources/`
- 交付给下游的结构片段：
  - 命令列表、执行顺序、cwd、timeout、可跳过条件
  - `requires_confirmation`
  - `write_effects`
  - `estimated_scope`

## dependencies

- 前置步骤：
  - `define-shared-helper-and-tests`
  - `collect-change-context`
  - `classify-impact`
- 依赖节点：
  - 共享 helper 中的命令模板和 status 枚举
  - `maintenance_gate_request.intent`
  - `maintenance_gate_request.verification_level`
- 需要人工确认的位置：
  - 当前阶段不引入 REVIEW；只负责把“哪些命令需要确认”写进 proposal

## implementation_suggestions

- 使用确定性脚本根据类别和风险规则拼装命令候选，例如 `python scripts/doctor_lgwf_wf_tools.py`、`python scripts/doctor_lgwf_wf_tools.py --deep`、`python -m unittest discover workflows/<id>/tests`、`python workflows/self-improve/scripts/self_improve.py workflow-health`、`python workflows/self-improve/scripts/self_improve.py pre-release ...`、`python scripts/package_lgwf_wf_tools_zip.py --force`。
- 把每条命令的 `write_effects` 明确到目录级别，例如 `.local/doctor/`、`.local/self-improve/`、`skills/lgwf-wf-tools/output/`，供 REVIEW 阶段完整展示。
- 对 `verification_level=full` 设计额外验证集合，但仍要受 `allow_*` 开关约束，不能因为等级高就绕过显式禁用。
- 针对 `output_zip` 已存在的情况给出明确策略，优先要求通过 REVIEW 决定是否改路径或继续，而不是在运行阶段静默覆盖。
- 资源目录中可放命令模板、写入影响说明和 timeout 建议，不要在脚本里散落硬编码文字。

## 修订补充：verification matrix 与计划 schema

计划阶段必须从 `impact_classification.json` 生成以下矩阵结果，不得仅输出自然语言建议。

| 条件 | 默认命令 | 开关约束 | write effects | short circuit | skip reason |
| --- | --- | --- | --- | --- | --- |
| 任意 `facade_entry`、`workflow_source`、`shared_contract`、`vendor`、`packaging` | `python scripts/doctor_lgwf_wf_tools.py` | 无 | `[]` 或脚本自身只读输出 | true | 无 |
| `shared_contract`、`vendor`、`entry_contract.json`、`workflow.lgwf` 或 `verification_level=full` | `python scripts/doctor_lgwf_wf_tools.py --deep` | `allow_deep_doctor=true` | `.local/doctor/` | false | `allow_deep_doctor=false` |
| `workflow_source` 或 `workflow_tests` 且存在 impacted workflow | `python -m unittest discover workflows/<id>/tests` | `allow_workflow_tests=true` | `[]` | false | `allow_workflow_tests=false` 或 tests 目录不存在 |
| `self_improve` | `python workflows/self-improve/scripts/self_improve.py workflow-health` | 无 | `.local/self-improve/` | false | 无 |
| `self_improve` 或 `verification_level=full` | `python workflows/self-improve/scripts/self_improve.py pre-release --source wf-maintenance-gate` | `allow_pre_release=true` | `.local/self-improve/` | false | `allow_pre_release=false` |
| `packaging` 或 `intent=package_ready` | `python scripts/package_lgwf_wf_tools_zip.py --force --output <output_zip>` | `allow_package_smoke=true` 且 zip 冲突已确认 | `skills/lgwf-wf-tools/output/` | false | `allow_package_smoke=false` 或 `output_zip` 冲突未确认 |
| 仅 `docs_only` 且 `verification_level=light` | 无强制命令 | 无 | `[]` | false | `docs_only_light` |

`verification_plan_proposal.json` 的每条 command 至少包含：

```json
{
  "check_id": "doctor_basic",
  "source": {
    "categories": ["workflow_source"],
    "files": ["skills/lgwf-wf-tools/workflows/wf-create/wf/workflow.lgwf"],
    "reason": "workflow source 变更至少需要 facade doctor"
  },
  "command": ["python", "scripts/doctor_lgwf_wf_tools.py"],
  "cwd": "skills/lgwf-wf-tools",
  "timeout_seconds": 120,
  "write_effects": [],
  "requires_allow": null,
  "can_skip": false,
  "skip_reason": null,
  "short_circuit": true
}
```

输出 zip 冲突策略：

- 若 `allow_package_smoke=true` 但 `output_zip` 已存在，proposal 必须设置 `zip_conflict.status="needs_review"`。
- 未经 REVIEW 显式确认，不得把 `--force` 命令放入可执行 `commands`；只能放入 `blocked_commands` 或 `suggested_commands`。
- REVIEW 可选择 `use_new_path` 或 `allow_overwrite`；运行阶段只能执行确认后的选择。

## acceptance_notes

- 重点确认 proposal 中每条命令都有来源说明，维护者能看懂“为什么这次要跑它”。
- 重点确认 deep doctor、pre-release 和 package smoke 只在开关允许时进入计划，否则最多作为可选建议，不进入已执行命令列表。
- 重点确认 zip 冲突策略、长耗时检查的 timeout 和失败后的 short-circuit 规则在 proposal 层就已经可审阅，不把关键决策推迟到运行阶段。

## out_of_scope

- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 在本阶段真实执行 doctor、unit test、pre-release 或 zip 打包
