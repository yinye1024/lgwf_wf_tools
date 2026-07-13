# implement_steps_react

## 职责

根据已确认的 `.lgwf/step_designs.json` 和脚手架结果生成目标 workflow package 初稿，并通过 ReAct 循环把实现、确定性 audit observe 和继续/退出决策闭环。

本阶段是 `wf-create` 的实现阶段子 workflow，不是独立 Codex skill，也不单独注册到 facade。

## 入口

- workflow：`workflow.lgwf`
- 父级调用：`wf/workflow.lgwf` 中的 `implement_steps_react`
- 内部编排：`initialize_implementation_observe -> REACT implement_steps_react`

## 子流程边界

- `01_implement_units/workflow.lgwf`：ACT 子 workflow，负责准备 implementation units、逐个执行 unit 并合并结果。
- `01_implement_units/01_implement_one_unit/workflow.lgwf`：ACT 内部第三层 workflow，负责单个 unit 的 context、Codex staging 输出和发布。它有独立输入、输出、失败恢复、staging 目录和 schema 注入边界，因此独立成孙级 workflow。
- `02_observe_audit/workflow.lgwf`：OBSERVE 子 workflow，负责确定性 audit 与 observe 归纳。

父级只通过 `.lgwf/implementation_reason.md`、`.lgwf/implementation_result.json`、`.lgwf/implementation_audit_result.json`、`.lgwf/implementation_observe.json` 和 `.lgwf/implementation_decision.json` 交接，不读取子流程私有 prompt、script 或运行中临时文件。

## 输入

- `.lgwf/implementation_context.json`
- `.lgwf/scaffold_package_result.json`，其中 `scaffold_plan` 是 package profile、目录、文件、placeholder 和阶段 manifest 的结构事实源
- `.lgwf/step_designs.json`
- `.lgwf/create_reference_context/implementation-reference-index.md`
- `.lgwf/create_reference_context/` 中由 implementation index 按需路由的 DSL、audit 和模块化参考资料
- 可选的上一轮 `.lgwf/implementation_result.json`、`.lgwf/implementation_audit_result.json`、`.lgwf/implementation_observe.json` 和 `.lgwf/implementation_decision.json`

## 输出

- `.lgwf/implementation_reason.md`
- `.lgwf/implementation_units.json`
- `.lgwf/current_implementation_unit_context.json`
- `.lgwf/current_implementation_unit_result.json`
- `.lgwf/implementation_result.json`
- `.lgwf/implementation_audit_result.json`
- `.lgwf/implementation_observe.json`
- `.lgwf/implementation_decision.json`

## 状态边界

运行状态只写入当前 run 的 `.lgwf/`。单 unit Codex 只能写 `.lgwf/implementation_stage/<unit_id>/` 下的 staging 文件，最终目标 package 由发布脚本复制，不允许 Codex 直接写 `target_package_abs`。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests
```

## 禁止事项

- 不绕过 `.lgwf/step_designs.json` 自行扩大实现范围。
- 不自动调用 `lgwf-wf-prompt-fix`、不自动注册 facade、不承诺端到端业务运行成功。
- 不向目标 package 根目录写入 `.lgwf`。
- 不通过 `..`、绝对路径或盘符路径读取父级或宿主仓库资料。
