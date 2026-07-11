# wf-maintenance-gate 工作流开发文档

## 文档用途

本文用于提交给 `wf-create`，作为创建 `skills/lgwf-wf-tools/workflows/wf-maintenance-gate` 的输入资料。目标不是在本文中直接实现 workflow，而是把维护收尾 gate 的真实意图、边界、输入输出、阶段设计和验收要求整理成可确认的 LGWF workflow 创建需求。

`wf-create` 启动时应把本文作为 `request.target_file`，并以本文的“目标形态”“业务流设计”和“验收要求”为准进行需求确认、业务流确认、步骤设计和初稿实现。

## 资料来源

- `README.md`
- `skills/lgwf-wf-tools/README.md`
- `skills/lgwf-wf-tools/AGENTS.md`
- `skills/lgwf-wf-tools/registry.json`
- `skills/lgwf-wf-tools/docs/maintenance.md`
- `skills/lgwf-wf-tools/docs/self-improve.md`
- `skills/lgwf-wf-tools/docs/workflow-inputs.md`
- `skills/lgwf-wf-tools/workflows/01-share/module-contract.md`
- `skills/lgwf-wf-tools/docs/LGWF_WF_MODULAR_DEVELOPMENT.md`
- `skills/lgwf-wf-tools/workflows/self-improve/scripts/pre_release_check.py`
- `skills/lgwf-wf-tools/scripts/doctor_lgwf_wf_tools.py`
- `skills/lgwf-wf-tools/scripts/package_lgwf_wf_tools_zip.py`

## 当前状态

`lgwf-wf-tools` 已经具备较完整的单项维护能力：

- `doctor_lgwf_wf_tools.py` 可做 facade 健康检查，`--deep` 可生成完整诊断报告。
- `self-improve pre-release` 可串联 doctor、changed files、self eval、workflow health、trace eval、scorecard 和 upgrade report。
- `package_lgwf_wf_tools_zip.py` 可把整个 facade skill 打包为 zip，并排除 `.local/`、`.lgwf/` 等运行态目录。
- `wf-create`、`wf-fix`、`wf-convert`、`wf-prompt-fix`、`wf-prompt-upgrade`、`wf-dsl-upgrade`、`e2e-test-generator`、`wf-post-fix` 和 `skill-packaging` 分别覆盖创建、修复、转换、prompt 质量、DSL 升级、测试生成、后续验收和打包特定场景。

当前缺口不是单项能力不足，而是缺少一个面向日常开发收尾的统一 gate：当维护者修改了 workflow、prompt、脚本、registry、文档或 vendor 后，需要先判断影响范围，再选择最小但足够的验证集合，最后汇总是否可以打包或发布。这个判断目前依赖人工经验，容易出现验证过重、验证遗漏或结果分散的问题。

## 创建目标

创建一个 registry 管理的内部 `lgwf_workflow_package`：`wf-maintenance-gate`。

目标 workflow 用于在一次变更完成后执行维护收尾：

1. 收集当前 git 变更和显式输入的变更范围。
2. 按模块和文件类型分类影响面。
3. 根据影响面生成验证计划。
4. 在执行耗时或写入型步骤前展示人工确认。
5. 执行只读健康检查、相关测试、可选 deep doctor、可选 self-improve pre-release、可选 zip 打包 smoke。
6. 汇总验证结论、失败项、关键产物、建议路由和后续动作。

该 workflow 的定位是“维护 gate”和“发布准备前检查”，不是替代具体修复 workflow。发现问题后，应建议路由到 `wf-fix`、`wf-prompt-fix`、`wf-prompt-upgrade`、`wf-dsl-upgrade`、`e2e-test-generator` 或 `self-improve`。

## 非目标

- 不自动修复失败项。
- 不自动提交 git、创建分支、创建 PR 或发布 zip。
- 不自动修改 `registry.json`、workflow 源码、vendor 文件或目标 package。
- 不覆盖或删除 `.local/`、`.lgwf/`、`ws/`、`output/` 中已有运行记录。
- 不替代 `wf-post-fix` 对单个目标 workflow 的完整后续验收。
- 不把内部 workflow 注册为独立 Codex skill。
- 不在未确认时执行打包、覆盖输出 zip 或长耗时全量测试。

## 目标模块形态

- 模块 id：`wf-maintenance-gate`
- 模块类型：`lgwf_workflow_package`
- 目标目录：`skills/lgwf-wf-tools/workflows/wf-maintenance-gate`
- workflow root：`skills/lgwf-wf-tools/workflows/wf-maintenance-gate/wf`
- workflow 入口：`skills/lgwf-wf-tools/workflows/wf-maintenance-gate/wf/workflow.lgwf`
- work dir：`skills/lgwf-wf-tools/workflows/wf-maintenance-gate/ws`
- registry entry：新增到 `skills/lgwf-wf-tools/registry.json`，不作为独立 Codex skill 暴露。

建议 registry 形态：

```json
{
  "id": "wf-maintenance-gate",
  "kind": "lgwf",
  "description": "根据当前变更影响面生成维护验证计划，执行确认后的健康检查、测试、发布前检查和可选打包 smoke，并汇总可发布性结论。",
  "workflow_lgwf": "workflows/wf-maintenance-gate/wf/workflow.lgwf",
  "work_dir": "workflows/wf-maintenance-gate/ws",
  "agents_md": "workflows/wf-maintenance-gate/AGENTS.md",
  "entry_contract": "workflows/wf-maintenance-gate/entry_contract.json"
}
```

## 输入契约建议

建议第一版使用 `input_json_required`，核心字段为 `maintenance_gate_request`。

```json
{
  "maintenance_gate_request": {
    "scope": "changed_files",
    "changed_files": [],
    "target_workflows": [],
    "intent": "pre_release_check",
    "verification_level": "standard",
    "allow_deep_doctor": false,
    "allow_workflow_tests": true,
    "allow_pre_release": false,
    "allow_package_smoke": false,
    "output_zip": "skills/lgwf-wf-tools/output/lgwf-wf-tools.zip"
  }
}
```

字段说明：

- `scope`：建议支持 `changed_files`、`explicit_files` 和 `full_facade`。默认 `changed_files`。
- `changed_files`：可选。为空时由 workflow 通过 `git status --short` 和 `git diff --name-only` 收集。
- `target_workflows`：可选。维护者已知影响的 workflow id，例如 `wf-create`、`wf-dsl-upgrade`。
- `intent`：建议支持 `local_check`、`pre_release_check`、`package_ready`。默认 `local_check`。
- `verification_level`：建议支持 `light`、`standard`、`full`。默认 `standard`。
- `allow_deep_doctor`：是否允许执行 `doctor --deep` 并写入 `.local/doctor/`。
- `allow_workflow_tests`：是否允许运行目标 workflow 的 unittest。
- `allow_pre_release`：是否允许执行 `self-improve pre-release`。
- `allow_package_smoke`：是否允许执行 `package_lgwf_wf_tools_zip.py` 的打包 smoke。
- `output_zip`：可选。只有 `allow_package_smoke=true` 且确认通过时才使用。

建议 `auto_human_policy` 设为 `forbidden`。原因是该 workflow 需要根据变更影响确认验证范围，且可能触发耗时检查或写入 `output/` 的打包 smoke。

## 输出契约建议

机器可读产物写入 `ws/.lgwf/`：

- `.lgwf/change_context.json`
- `.lgwf/impact_classification.json`
- `.lgwf/verification_plan_proposal.json`
- `.lgwf/verification_plan_confirmation_context.json`
- `.lgwf/verification_plan_approval.json`
- `.lgwf/verification_plan.json`
- `.lgwf/verification_results.json`
- `.lgwf/failure_routes.json`
- `.lgwf/maintenance_gate_summary.json`

面向人的报告写入：

- `ws/reports/wf-maintenance-gate/report.md`

如果执行了可选打包 smoke，输出 zip 默认写入：

- `skills/lgwf-wf-tools/output/lgwf-wf-tools.zip`

该 zip 属于明确确认后的产物，不得覆盖 `.local/`、`.lgwf/` 或其他运行历史。打包脚本本身已经排除运行态目录，workflow 仍应在报告中展示排除规则摘要。

## 业务流设计

根 `wf/workflow.lgwf` 只做薄编排，阶段细节放入第一层子 workflow。建议阶段如下。

### 01_collect_change_context

目标：收集维护 gate 的输入上下文。

职责：

- 读取 `maintenance_gate_request`。
- 如果 `changed_files` 为空，收集 git changed files。
- 读取 registry workflow 列表。
- 识别当前仓库根目录、facade 根目录、目标 workflow 目录和脚本目录。
- 输出 `change_context.json`。

禁止事项：

- 不修改文件。
- 不执行测试。
- 不读取 `.local/` 历史作为判断依据，除非后续阶段明确需要引用报告路径。

### 02_classify_impact

目标：把变更文件映射为验证影响面。

建议分类：

- `facade_entry`：`SKILL.md`、`AGENTS.md`、`registry.json`、`README.md`。
- `workflow_source`：`workflows/*/wf/**`、`workflows/*/AGENTS.md`、`workflows/*/entry_contract.json`。
- `workflow_tests`：`workflows/*/tests/**`。
- `shared_contract`：`workflows/01-share/**`、`docs/LGWF_WF_MODULAR_DEVELOPMENT.md`。
- `scripts`：`scripts/**`。
- `self_improve`：`workflows/self-improve/**`。
- `vendor`：`vendor/lgwf-client-assist/**`。
- `docs_only`：普通 Markdown 文档和模板。
- `packaging`：`scripts/package_lgwf_wf_tools_zip.py`、`scripts/package_lgwf_skill.py`、`workflows/skill-packaging/**`。

输出：

- 每个文件的分类。
- 受影响 workflow id。
- 风险等级：`low`、`medium`、`high`。
- 推荐验证候选。

### 03_plan_verification

目标：根据影响面生成可确认的验证计划。

建议规则：

- 任意 registry、entry contract、workflow source 变更：至少运行 `doctor_lgwf_wf_tools.py`。
- `workflow.lgwf`、entry contract 或共享契约变更：建议运行 `doctor --deep`。
- 某个 workflow 目录变更：建议运行该 workflow 的 `tests`。
- `self-improve` 变更：建议运行 `workflows/self-improve/tests` 和 `self_improve.py workflow-health`。
- vendor 变更：建议运行 `init`/doctor 相关测试和 `doctor`。
- 打包脚本变更：建议运行对应 package tests 和 zip smoke。
- `verification_level=full`：建议增加 `self-improve pre-release --run-workflow-tests`。

输出 `verification_plan_proposal.json`，至少包含：

- `commands`：待执行命令、cwd、timeout、是否写入本地状态、是否可跳过。
- `requires_confirmation`：是否需要人工确认。
- `write_effects`：会写入哪些目录，例如 `.local/doctor/`、`.local/self-improve/`、`output/`。
- `estimated_scope`：light、standard 或 full。

### 04_confirm_verification_plan

目标：在执行耗时或写入型步骤前确认验证计划。

确认内容必须包含：

- 变更摘要。
- 风险等级。
- 将执行的命令。
- 会写入的产物目录。
- 可选决策：`approve`、`revise`、`reject`。

`approve` 后固化 `verification_plan.json`。`revise` 必须携带完整修订计划。`reject` 终止 workflow。

### 05_run_verification

目标：按确认计划执行验证命令。

职责：

- 顺序执行确认后的命令。
- 捕获 return code、stdout 摘要、stderr 摘要和关键 JSON payload。
- 超时或失败时继续记录结果，但可按计划字段决定是否短路。
- 不自动修复失败。

建议优先复用现有脚本：

- `python scripts/doctor_lgwf_wf_tools.py`
- `python scripts/doctor_lgwf_wf_tools.py --deep`
- `python -m unittest discover workflows/<id>/tests`
- `python workflows/self-improve/scripts/self_improve.py workflow-health`
- `python workflows/self-improve/scripts/self_improve.py pre-release --version <version> --source wf-maintenance-gate`
- `python scripts/package_lgwf_wf_tools_zip.py --force`

### 06_summarize_gate_result

目标：生成维护 gate 结论。

报告应包含：

- 总体状态：`pass`、`fail` 或 `needs_review`。
- 变更影响分类。
- 已执行验证命令和结果。
- 关键产物路径。
- 失败项摘要。
- 建议路由：例如失败项属于 DSL audit 则建议 `wf-dsl-upgrade` 或 `wf-fix`，prompt 契约问题建议 `wf-prompt-fix`，发布前治理问题建议 `self-improve`。
- 后续建议：是否可以继续打包、是否需要人工复核、是否建议运行更高等级验证。

## 推荐目录结构

```text
wf-maintenance-gate/
  AGENTS.md
  README.md
  entry_contract.json
  tests/
  ws/
  wf/
    workflow.lgwf
    artifact_contracts.json
    shared/
      scripts/
        maintenance_gate_common.py
    01_collect_change_context/
      workflow.lgwf
      agents/
      scripts/
      resources/
    02_classify_impact/
      workflow.lgwf
      agents/
      scripts/
      resources/
    03_plan_verification/
      workflow.lgwf
      agents/
      scripts/
      resources/
    04_confirm_verification_plan/
      workflow.lgwf
      agents/
      scripts/
      resources/
    05_run_verification/
      workflow.lgwf
      agents/
      scripts/
      resources/
    06_summarize_gate_result/
      workflow.lgwf
      agents/
      scripts/
      resources/
```

不创建 `wf/<stage>/<substage>/workflow.lgwf`。每个阶段的 prompt、脚本、资源留在对应阶段目录内。跨阶段稳定 helper 才放入 `wf/shared/scripts/`。

## 状态边界

- 源码目录：`skills/lgwf-wf-tools/workflows/wf-maintenance-gate/`
- workflow root：`skills/lgwf-wf-tools/workflows/wf-maintenance-gate/wf/`
- runtime work dir：`skills/lgwf-wf-tools/workflows/wf-maintenance-gate/ws/`
- runtime 状态：`skills/lgwf-wf-tools/workflows/wf-maintenance-gate/ws/.lgwf/`
- 报告目录：`skills/lgwf-wf-tools/workflows/wf-maintenance-gate/ws/reports/wf-maintenance-gate/`

源码目录不得保存 `.lgwf/`、`.local/`、`__pycache__/` 或运行临时文件。

## 文档契约要求

目标 package 必须补齐：

- `AGENTS.md`：模块定位、入口、依赖、状态边界、产物、验证和禁止事项。
- `README.md`：维护者视角的用途、输入、阶段、产物和运行方式。
- `entry_contract.json`：输入 schema、auto-human 策略、状态边界、输出和 resume 规则。
- `wf/artifact_contracts.json`：关键运行产物、确认后固化产物和报告。

## 验收要求

第一版创建完成后至少满足：

1. registry 中新增 `wf-maintenance-gate`，且 `validate_registry.py` 通过。
2. `wf/workflow.lgwf` 是薄编排，只引用第一层阶段 workflow。
3. 所有阶段目录自包含 `workflow.lgwf` 和必要的 `agents/`、`scripts/`、`resources/`。
4. `entry_contract.json` 符合 `entry_contract` 共享规范。
5. `AGENTS.md`、`README.md`、`entry_contract.json` 与 `artifact_contracts.json` 的入口、状态边界和产物描述一致。
6. `doctor_lgwf_wf_tools.py` 通过。
7. 新增 focused tests 覆盖 impact classification、verification plan generation、registry path 和 artifact contract。
8. 最小运行 smoke 可在不修改源码的情况下生成 `maintenance_gate_summary.json`。

## 后续可选增强

- 增加 `changed_files` 到 workflow id 的更精确映射。
- 支持读取 `.local/doctor/latest.json` 作为失败路由参考。
- 支持把失败项整理为 `self-improve` incident 草稿，但必须人工确认后才能记录。
- 支持 `package_ready` 模式下自动展示 zip 产物路径和 SHA-256。
- 支持按目标 workflow 自动建议是否运行 `wf-post-fix`。
