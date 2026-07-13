# implement_units

## 职责

把本轮 `.lgwf/implementation_reason.md` 转换为可独立执行的 implementation units，逐个调用单 unit workflow，并合并为 `.lgwf/implementation_result.json`。

## 入口

- workflow：`workflow.lgwf`
- 父级调用：`04_implement_steps_react/workflow.lgwf` 的 `ACT WORKFLOW implement_units`

## 输入

- `.lgwf/implementation_context.json`
- `.lgwf/implementation_observe.json`
- `.lgwf/implementation_reason.md`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/step_designs.json`

## 输出

- `state.lgwf_wf_create.implementation_units`
- `state.lgwf_wf_create.implementation_unit_results.items`
- `.lgwf/implementation_units.json`
- `.lgwf/implementation_result.json`

## 子流程

`01_implement_one_unit/workflow.lgwf` 负责单个 unit 的 staging 输出和发布。ACT 父流程不直接读取该子流程的 prompt、resource 或脚本，只通过 FOREACH 当前项、结果状态和 workspace artifact 交接。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests -p test_implementation_units.py
```

## 禁止事项

- 不直接生成目标 package 文件；目标写入由单 unit 发布脚本完成。
- 不修改 OBSERVE 产物。
- 不绕过 `01_implement_one_unit/workflow.lgwf` 直接调用单 unit Codex。
