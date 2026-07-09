# skill-packaging

`skill-packaging` 是一个内部 LGWF workflow package，用于把带 `wf/workflow.lgwf` 的 Codex skill 打包成自包含 skill。它采用“外层 package + 内层 `wf/` workflow root”的结构，真实入口固定为 [wf/workflow.lgwf](/D:/allen/github/lgwf_wf_tools/skills/lgwf-wf-tools/workflows/skill-packaging/wf/workflow.lgwf)。

当前目录已经把原脚本型能力收敛成可审计、可确认、可恢复的六阶段 LGWF workflow，并由 facade `registry.json` 以 `kind=lgwf` 派发。根目录 `scripts/package_lgwf_skill.py` 只保留为旧脚本兼容入口，不是本模块的 registry 入口。

## 模块定位

- 模块类型：`lgwf_workflow_package`
- registry id：`skill-packaging`
- 作用：把带 `wf/workflow.lgwf` 的源 Codex skill 复制到批准后的输出目录，并补齐内置 `vendor/lgwf-client-assist` runtime、本地 runner、`PACKAGING_MANIFEST.json`、验证结果和总结报告。
- 该目录是 facade 管理的内部 workflow package，不是独立 Codex skill；registry 入口使用 `wf/workflow.lgwf` 和 `ws/`。

## 入口

- workflow root：`workflows/skill-packaging/wf/workflow.lgwf`
- work dir：`workflows/skill-packaging/ws`
- 输入契约：`entry_contract.json`
- 推荐启动命令：`python skills\lgwf-wf-tools\scripts\run_skill_workflow.py --workflow-id skill-packaging --input-json-file <packaging-request.json>`
- 入口 JSON 需要提供 `packaging_request` 对象，最小字段为 `source_skill` 与 `output_parent`。

## 依赖

- 默认依赖仓库内 `skills/lgwf-wf-tools/vendor/lgwf-client-assist/` 作为 bundled runtime 来源。
- 依赖源 skill 至少包含 `SKILL.md`、`AGENTS.md`、`README.md` 和 `wf/workflow.lgwf`。
- 依赖 `ws/` 作为独立运行目录，运行态状态只写入 `ws/.lgwf/`，报告只写入 `ws/reports/skill-packaging/`。
- `source_skill`、`runtime_source`、`output_parent` 可以是 workspace 相对路径或运行时绝对路径；这些值属于运行时输入边界，不会被写回 package 内 authoring 资源路径。

## 状态边界

- package 源码入口只在 `wf/` 下，外层目录不放可运行 `workflow.lgwf`。
- workflow source root 与 work dir 必须分离；运行状态只写 `ws/.lgwf/`，不得写回当前 package 源码树。
- 报告只写 `ws/reports/skill-packaging/`。
- 真正的业务写入只允许落到用户批准后的 `output_parent/<source-skill-name>/`。

## 产物

- 运行态 `.lgwf/` 产物：`packaging_request.json`、`packaging_path_context.json`、`runtime_source_resolution.json`、`packaging_write_scope.json`、`packaging_preflight.json`、`packaging_plan_proposal.json`、`packaging_plan_confirmation_context.json`、`packaging_plan_approval.json`、`confirmed_packaging_plan.json`、`materialized_package.json`、`package_validation.json`、`packaging_result_summary.json`
- 报告：`reports/skill-packaging/packaging_result_report.md`
- 批准后输出目录：`<output_parent>/<source-skill-name>/`
- 关键打包产物：`<output_parent>/<source-skill-name>/vendor/lgwf-client-assist/`、`<output_parent>/<source-skill-name>/scripts/run_local_lgwf_workflow.py`、`<output_parent>/<source-skill-name>/PACKAGING_MANIFEST.json`

## 验证

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\skill-packaging\wf\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\skill-packaging\tests
```

只改入口文档时，仍需检查 UTF-8 no BOM、命令示例、相对路径示例以及 `wf/` / `ws/` 边界描述是否与当前目录一致。

## 禁止事项

- 不要在当前 package 根目录生成 `workflow.lgwf`。
- 不要在 `wf/<stage>/` 下继续创建孙级 `workflow.lgwf`。
- 不要把运行状态写入 package 源码树或打包产物根目录 `.lgwf/`。
- 不要绕过 `03_confirm_packaging_plan` 的人工确认直接写打包产物目录。
- 不要在 authoring 资源路径里使用绝对路径、盘符路径或 `..`。
- 运行期间不要自动改 facade `registry.json`、根目录打包脚本或发布流程。

## 阶段

1. `01_prepare_packaging_request`：规范化输入并冻结写入边界。
2. `02_preflight_packaging_plan`：预检源 skill、runtime 和目标目录，生成计划草案。
3. `03_confirm_packaging_plan`：展示计划并显式人工确认。
4. `04_materialize_packaged_skill`：按确认计划执行真实打包。
5. `05_verify_packaged_skill`：验证结构、manifest、runtime 和 authoring audit smoke。
6. `06_summarize_packaging_result`：汇总结果并输出报告。

## 输入摘要

当前 workflow 直接消费 `packaging_request` JSON：

```json
{
  "packaging_request": {
    "source_skill": "skills/example-skill",
    "output_parent": "dist",
    "runtime_source": "skills/lgwf-wf-tools/vendor/lgwf-client-assist",
    "force": false,
    "audit_smoke": true
  }
}
```

`source_skill` 与 `output_parent` 可以是 workspace 相对路径或绝对路径。绝对路径只作为运行时输入存在，不会写回 authoring 资源路径。

## Approval 边界

- 只有 `03_confirm_packaging_plan` 会做人审。
- `approve` 前不得真实写入 `output_parent/<source-skill-name>/`。
- `revise` 只允许回到同一确认阶段闭环。
- `reject` 直接终止整个 workflow。

## 非目标

- 不维护根目录旧脚本入口的兼容行为。
- 不做 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成。
- 不做自动修复、自动重试或端到端成功保证。
