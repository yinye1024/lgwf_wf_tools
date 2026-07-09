# skill-packaging 工作流指引

本目录是 `lgwf-wf-tools/workflows/skill-packaging` 下的内部 LGWF workflow package，用于把带 `wf/workflow.lgwf` 的 Codex skill 打包成内置 `lgwf-client-assist` runtime 的自包含 skill。当前目录由 facade `registry.json` 以 `kind=lgwf` 派发，不是独立 Codex skill。

## 模块契约

- 模块类型：`lgwf_workflow_package`。
- 真实入口固定为 `wf/workflow.lgwf`；外层根目录不再放可运行 `workflow.lgwf`。
- 模块边界遵循 [../01-share/module-contract.md](/D:/allen/github/lgwf_wf_tools/skills/lgwf-wf-tools/workflows/01-share/module-contract.md) 的 `lgwf_workflow_package` 契约。
- 输入契约、状态边界和最小运行方式以 [entry_contract.json](/D:/allen/github/lgwf_wf_tools/skills/lgwf-wf-tools/workflows/skill-packaging/entry_contract.json) 为准。
- [wf/artifact_contracts.json](/D:/allen/github/lgwf_wf_tools/skills/lgwf-wf-tools/workflows/skill-packaging/wf/artifact_contracts.json) 提供关键产物基线；本文件补充当前实现保留的运行态 Contract 说明。

## 模块定位

- 负责把源 skill 复制到输出目录。
- 负责内置 `vendor/lgwf-client-assist` runtime。
- 负责生成本地 runner、`PACKAGING_MANIFEST.json`、验证结果和总结报告。
- 负责显式人工确认打包计划。

当前不负责：

- 维护 facade 根 `scripts/package_lgwf_skill.py` 旧脚本入口的兼容行为。
- `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成、自动修复、自动重试或端到端成功保证。

## 入口

- workflow id：`skill-packaging`
- `workflow_lgwf`：`workflows/skill-packaging/wf/workflow.lgwf`
- `work_dir`：`workflows/skill-packaging/ws`
- 输入契约入口：`entry_contract.json` 负责声明 `packaging_request` schema、`--input-json-file` 策略和 resume 边界。
- 推荐启动命令：`python skills\lgwf-wf-tools\scripts\run_skill_workflow.py --workflow-id skill-packaging --input-json-file <packaging-request.json>`
- workflow root：`wf/workflow.lgwf`
- 阶段目录：
  - `wf/01_prepare_packaging_request/`
  - `wf/02_preflight_packaging_plan/`
  - `wf/03_confirm_packaging_plan/`
  - `wf/04_materialize_packaged_skill/`
  - `wf/05_verify_packaged_skill/`
  - `wf/06_summarize_packaging_result/`
- 共享 helper：`wf/shared/scripts/`
- 已批准步骤副本：`wf/docs/steps/`

## 依赖

- 依赖仓库根 `skills/lgwf-wf-tools/vendor/lgwf-client-assist/` 作为默认 runtime 来源。
- 依赖源 skill 至少包含 `SKILL.md`、`AGENTS.md`、`README.md` 和 `wf/workflow.lgwf`。
- 依赖运行时 work dir `ws/` 提供 `.lgwf/` 状态与 `reports/` 输出。

## 状态边界

- workflow 运行状态只写入 `ws/.lgwf/`。
- 面向人的报告只写入 `ws/reports/skill-packaging/`。
- 真正的业务写入只允许落到用户批准后的 `output_parent/<source-skill-name>/`。
- 不向本 package 根目录写 `.lgwf/`、`.tmp/`、`__pycache__/` 或临时运行文件。

## 产物

- `.lgwf/packaging_request.json`
- `.lgwf/packaging_path_context.json`
- `.lgwf/runtime_source_resolution.json`
- `.lgwf/packaging_write_scope.json`
- `.lgwf/packaging_preflight.json`
- `.lgwf/packaging_plan_proposal.json`
- `.lgwf/packaging_plan_confirmation_context.json`
- `.lgwf/packaging_plan_approval.json`
- `.lgwf/confirmed_packaging_plan.json`
- `.lgwf/materialized_package.json`
- `.lgwf/package_validation.json`
- `.lgwf/packaging_result_summary.json`
- `reports/skill-packaging/packaging_result_report.md`
- 用户批准后的打包产物目录：`<output_parent>/<source-skill-name>/`

## Approval 边界

- 只有 `03_confirm_packaging_plan` 会做人审。
- 固定三选项：`approve`、`revise`、`reject`。
- 只有 `approve` 后才能真实写入打包产物目录。
- `revise` 留在 `03_confirm_packaging_plan` 内部闭环。
- `reject` 直接终止整个 workflow。

## 验证

入口文档、DSL Contract 或说明文字改动后，至少执行以下校验：

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\skill-packaging\wf\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\skill-packaging\tests
```

只改文档时仍需保持 UTF-8 no BOM，并确认命令示例、路径示例和 `wf/`、`ws/` 边界与当前目录结构一致。

## 禁止事项

- 不要在根目录生成 `workflow.lgwf`。
- 不要生成 `wf/<stage>/<substage>/workflow.lgwf`。
- 不要把运行状态写入目标 package 源码树。
- 不要在 `internal_workflow_package` 下生成根 `SKILL.md`。
- 不要绕过 `03_confirm_packaging_plan` approval 直接写打包产物目录。
- 不要把 `source_skill`、`output_parent`、`runtime_source` 这类运行时输入路径改写成 package 内 authoring 资源路径。
- 运行期间不要自动改 facade 路由、registry 或发布流程。
