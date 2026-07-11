# skill-packaging 工作流创建意图与设计方案

## 文档用途

本文用于提交给 `wf-create`，作为创建或重建 `skills/lgwf-wf-tools/workflows/skill-packaging` 的输入资料。目标不是在本文中直接修改 workflow，而是把现有 `skill-packaging` 的真实意图、当前状态、目标边界和建议设计整理成可确认的 LGWF workflow 创建需求。

建议 `wf-create` 启动时把本文作为 `request.target_file`，并以本文的“目标形态”为准进行需求确认、业务流确认、步骤设计和初稿实现。

## 资料来源

- `skills/lgwf-wf-tools/registry.json`
- `skills/lgwf-wf-tools/workflows/skill-packaging/AGENTS.md`
- `skills/lgwf-wf-tools/workflows/skill-packaging/README.md`
- `skills/lgwf-wf-tools/workflows/skill-packaging/entry_contract.json`
- `skills/lgwf-wf-tools/workflows/skill-packaging/wf/**`
- `skills/lgwf-wf-tools/scripts/package_lgwf_skill.py`
- `skills/lgwf-wf-tools/tests/test_package_lgwf_skill.py`
- `skills/lgwf-wf-tools/workflows/01-share/module-contract.md`
- `skills/lgwf-wf-tools/docs/LGWF_WF_MODULAR_DEVELOPMENT.md`

## 当前状态

`skill-packaging` 当前在 registry 中声明为 `tool-workflow`，入口是 facade 根目录下的 `scripts/package_lgwf_skill.py`。该脚本已经具备可用的基础打包能力：

- 校验源 skill 必须包含 `SKILL.md`、`AGENTS.md`、`README.md` 和 `wf/workflow.lgwf`。
- 校验 runtime 目录必须包含 `AGENTS.md` 和 `scripts/lgwf.py`。
- 复制源 skill 文件树，并排除 `.git`、`.lgwf`、`.local`、`.mypy_cache`、`.pytest_cache`、`__pycache__`、`reports`、`ws`、`.pyc`、`.pyo`。
- 将 `lgwf-client-assist` runtime 复制到输出 skill 的 `vendor/lgwf-client-assist/`。
- 生成 `scripts/run_local_lgwf_workflow.py`，用于在打包后的 skill 内调用本地 runtime。
- 生成 `PACKAGING_MANIFEST.json`，记录 packager、源 skill、runtime、runner 和排除规则。
- 默认拒绝覆盖已有输出目录，只有显式 `force=true` 或 CLI `--force` 才允许覆盖。

同时，`workflows/skill-packaging/wf/` 中已经存在一个四阶段 LGWF 初稿和 `wf/docs/steps/*.md` 步骤设计材料。但 `AGENTS.md` 和 `README.md` 明确说该 `wf/` 目录只是历史设计材料，不是 registry 当前运行入口；部分阶段脚本也显示真实复制、runtime 内置、manifest 生成和 audit smoke 仍是占位说明。因此当前目录存在两类形态并存的问题：

- 可用执行面在 facade 根目录脚本 `skills/lgwf-wf-tools/scripts/package_lgwf_skill.py`。
- workflow 设计面在 `workflows/skill-packaging/wf/`，但尚未被 registry 作为 `lgwf_workflow_package` 启动。

## 创建目标

建议让 `wf-create` 将 `skill-packaging` 正式创建或升级为 registry 管理的内部 `lgwf_workflow_package`，用于把带 `wf/workflow.lgwf` 的 Codex skill 打包成内置 `lgwf-client-assist` runtime 的自包含 skill。

目标 workflow 应完成以下事情：

- 从用户输入中确认源 skill、输出父目录、可选 runtime 来源和覆盖策略。
- 在写入前进行确定性前置校验，明确源 skill 结构、runtime 完整性、目标目录状态、排除规则和覆盖风险。
- 在真实写入前展示打包计划并等待人工确认。
- 按确认计划执行确定性打包，复用或迁移当前 `package_lgwf_skill.py` 的核心能力。
- 对输出 skill 执行结构校验、manifest 校验、runtime 校验和最小 audit smoke。
- 输出结构化结果报告，说明输出目录、manifest 路径、验证结论、失败原因和后续建议。

目标 workflow 的用户价值是把当前“一次性 CLI 脚本”升级为“可审阅、可恢复、可追踪、有人工确认边界的 LGWF 打包流程”。

## 非目标

- 不修改 facade `vendor/lgwf-client-assist/` 内容，只允许复制到打包产物。
- 不自动发布、不自动安装到 Codex、不自动提交 git、不自动创建 PR。
- 不自动修改源 skill。
- 不自动注册或修改被打包 skill 的 registry。
- 不承诺打包后 workflow 的端到端业务成功，只承诺结构、runtime、runner 和 authoring audit smoke 的最小可用性。
- 不绕过人工确认执行覆盖写入。
- 不把运行态 `.lgwf/`、`ws/`、`.local/`、`reports/` 或缓存目录复制进发布产物。

## 目标模块形态

建议目标模块类型为 `lgwf_workflow_package`。

建议 registry 形态：

```json
{
  "id": "skill-packaging",
  "kind": "lgwf",
  "description": "把带 wf/workflow.lgwf 的 LGWF workflow Codex skill 打包成内置 lgwf-client-assist runtime 的自包含 skill。",
  "workflow_lgwf": "workflows/skill-packaging/wf/workflow.lgwf",
  "work_dir": "workflows/skill-packaging/ws",
  "agents_md": "workflows/skill-packaging/AGENTS.md",
  "entry_contract": "workflows/skill-packaging/entry_contract.json"
}
```

如果需要保留现有 CLI 兼容入口，建议把 `skills/lgwf-wf-tools/scripts/package_lgwf_skill.py` 改为薄包装器，调用 workflow 本地共享脚本中的确定性打包函数；或者明确把它保留为独立维护入口，但 registry 的正式运行入口以 `wf/workflow.lgwf` 为准。该决策应在 `wf-create` 的需求确认阶段由人工确认。

## 输入契约建议

建议第一版使用 `input_json_required`，避免 PowerShell 参数转义问题，也方便后续 resume 和报告记录。

建议输入结构：

```json
{
  "packaging_request": {
    "source_skill": "skills/wf-audit-fix",
    "output_parent": "outputs/packaged-skills",
    "runtime_source": "skills/lgwf-wf-tools/vendor/lgwf-client-assist",
    "force": false,
    "audit_smoke": true
  }
}
```

字段含义：

- `source_skill`：必填，源 Codex skill 目录，可以是工作区相对路径或用户提供的绝对路径。
- `output_parent`：必填，输出父目录，最终产物写入 `<output_parent>/<source_skill_name>`。
- `runtime_source`：可选，默认使用 facade 的 `skills/lgwf-wf-tools/vendor/lgwf-client-assist`。
- `force`：可选，默认 `false`；只有显式为 `true` 且计划确认通过时才允许覆盖输出目录。
- `audit_smoke`：可选，默认 `true`；用于控制是否对打包后 `wf/workflow.lgwf` 执行 authoring audit smoke。

`auto_human_policy` 建议第一版设为 `forbidden`。如果后续需要无人工确认的只读预检模式，应新增明确的 `dry_run` 输入，而不是复用正式写入流程。

## 业务流设计

建议不要直接照搬现有 `02/04/07/09` 的历史阶段名，而是用更贴近打包业务的阶段名。根 `wf/workflow.lgwf` 只做薄编排，阶段细节放入第一层子 workflow。

建议阶段：

1. `01_prepare_packaging_request`
   - 规范化输入 JSON。
   - 解析 `source_skill`、`output_parent`、`runtime_source`。
   - 固化路径上下文和写入范围。
   - 不做真实写入。

2. `02_preflight_packaging_plan`
   - 校验源 skill 结构。
   - 校验 runtime 结构。
   - 检查目标目录是否存在。
   - 生成复制排除规则、runner 生成计划、manifest 计划和 audit smoke 计划。
   - 输出 `packaging_plan_proposal`。

3. `03_confirm_packaging_plan`
   - 使用 `REVIEW` 或等价确认节点展示计划。
   - 决策建议为 `approve`、`revise`、`reject`。
   - `approve` 后固化 `confirmed_packaging_plan`。
   - `reject` 直接终止。
   - `revise` 重新生成确认上下文，不把 human decision record 当作业务对象。

4. `04_materialize_packaged_skill`
   - 根据已确认计划执行打包。
   - 复制源 skill，过滤运行态目录和缓存。
   - 复制 `lgwf-client-assist` 到 `vendor/lgwf-client-assist/`。
   - 生成 `scripts/run_local_lgwf_workflow.py`。
   - 生成 `PACKAGING_MANIFEST.json`。
   - 写入执行摘要。

5. `05_verify_packaged_skill`
   - 检查输出目录结构和关键文件。
   - 检查 `PACKAGING_MANIFEST.json` 字段。
   - 检查运行态目录和缓存未被复制。
   - 检查 runner 指向打包产物内的 `vendor/lgwf-client-assist/scripts/lgwf.py`。
   - 对输出 skill 的 `wf/workflow.lgwf` 执行 authoring audit smoke。
   - 验证失败时输出诊断，不自动修复。

6. `06_summarize_packaging_result`
   - 汇总确认计划、执行结果、验证结论。
   - 输出最终产物路径、manifest 路径、验证状态和后续建议。
   - 不自动触发 `wf-post-fix` 或其他下游 workflow。

## 状态与产物建议

运行状态只写入 `skills/lgwf-wf-tools/workflows/skill-packaging/ws/.lgwf/`。

建议 `.lgwf/` 产物：

- `packaging_request.json`
- `packaging_preflight.json`
- `packaging_plan_proposal.json`
- `packaging_plan_confirmation_context.json`
- `packaging_plan_approval.json`
- `confirmed_packaging_plan.json`
- `materialized_package.json`
- `package_validation.json`
- `packaging_result_summary.json`
- `reports/skill-packaging/packaging_result_report.md`

打包输出产物：

- `<output_parent>/<source_skill_name>/`
- `<output_parent>/<source_skill_name>/vendor/lgwf-client-assist/`
- `<output_parent>/<source_skill_name>/scripts/run_local_lgwf_workflow.py`
- `<output_parent>/<source_skill_name>/PACKAGING_MANIFEST.json`

## 目录设计建议

建议目标目录保持“外层 package + 内层 `wf/` workflow root”的结构：

```text
workflows/skill-packaging/
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
        packaging_common.py
    docs/
      steps/
    01_prepare_packaging_request/
      workflow.lgwf
      agents/
      scripts/
      resources/
    02_preflight_packaging_plan/
      workflow.lgwf
      agents/
      scripts/
      resources/
    03_confirm_packaging_plan/
      workflow.lgwf
      agents/
      scripts/
      resources/
    04_materialize_packaged_skill/
      workflow.lgwf
      agents/
      scripts/
      resources/
    05_verify_packaged_skill/
      workflow.lgwf
      agents/
      scripts/
      resources/
    06_summarize_packaging_result/
      workflow.lgwf
      agents/
      scripts/
      resources/
```

根目录不得放可运行的 `workflow.lgwf`。`workflow.lgwf` 只能出现在 `wf/workflow.lgwf` 和 `wf/<stage>/workflow.lgwf`。

## 实现策略建议

优先复用当前已测试过的 `package_lgwf_skill.py` 逻辑，但需要解决它当前位于 facade 根 `scripts/` 的问题。推荐方案：

1. 将确定性打包函数抽取到 `workflows/skill-packaging/wf/shared/scripts/packaging_common.py` 或阶段私有脚本中。
2. 让 `04_materialize_packaged_skill` 调用 workflow 本地脚本完成真实打包。
3. 保留 `skills/lgwf-wf-tools/scripts/package_lgwf_skill.py` 作为兼容 CLI，内部调用同一份打包函数，避免逻辑分叉。
4. 更新 `AGENTS.md`、`README.md`、`entry_contract.json`，让它们明确当前模块是 `lgwf_workflow_package`，不再称 `wf/` 为历史材料。

如果短期内不迁移 CLI 脚本，也必须在 workflow 文档中明确该跨目录依赖，并把最小验证覆盖到 registry 入口、脚本入口和 workflow 入口的一致性。

## 验证建议

创建完成后至少执行：

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\skill-packaging\wf\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\skill-packaging\tests
python -m unittest discover skills\lgwf-wf-tools\tests -p test_package_lgwf_skill.py
python -m unittest discover skills\lgwf-wf-tools\tests -p test_registry_workflow_paths.py
```

建议增加 smoke fixture：

- 构造一个最小源 skill，包含 `SKILL.md`、`AGENTS.md`、`README.md`、`wf/workflow.lgwf`、`ws/.lgwf/`、`.local/`、`reports/` 和 `scripts/tool.py`。
- 运行 `skill-packaging` workflow 打包到临时输出目录。
- 验证打包产物存在 `vendor/lgwf-client-assist/scripts/lgwf.py`、`scripts/run_local_lgwf_workflow.py` 和 `PACKAGING_MANIFEST.json`。
- 验证 `ws/`、`.local/`、`reports/`、`__pycache__/` 未被复制。
- 验证未传 `force` 时拒绝覆盖已有输出目录。

## 风险与待确认点

- 需要确认是否正式把 registry 中 `skill-packaging.kind` 从 `tool-workflow` 改为 `lgwf`。
- 需要确认现有 facade 根 CLI 是否保留为兼容入口，还是完全由 workflow 入口替代。
- 需要确认 `force=true` 的覆盖行为是否只需要一次计划确认，还是需要单独的高风险覆盖确认。
- 需要确认 audit smoke 的失败策略：第一版建议只报告失败，不自动修复。
- 需要确认输出目录允许绝对路径输入；如果允许，必须只作为运行时目标路径，不得写入 workflow resource path。

## 建议的 wf-create 启动输入

后续提交给 `wf-create` 时可使用以下输入。由于包含中文和嵌套 JSON，建议写入 UTF-8 no BOM JSON 文件后使用 `--input-json-file`。

```json
{
  "raw_intent": "请根据计划文档创建或重建 registry 内部 LGWF workflow package：skill-packaging。目标是把当前脚本型 skill 打包能力升级为可审阅、可恢复、可验证的 LGWF workflow，用于把带 wf/workflow.lgwf 的 Codex skill 打包成内置 lgwf-client-assist runtime 的自包含 skill。目标、输入输出、阶段设计、状态边界、验证和非目标以计划文档为准。",
  "request": {
    "target_file": "D:/allen/github/lgwf_wf_tools/docs_tmp/skill-packaging-wf-create-intent-design.md"
  }
}
```
