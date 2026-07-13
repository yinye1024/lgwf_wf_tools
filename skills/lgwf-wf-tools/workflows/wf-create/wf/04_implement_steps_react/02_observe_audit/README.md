# observe_audit

## 职责

对实现阶段 ACT 输出的目标 workflow package 初稿执行确定性 audit，并把 audit 结果归纳为下一轮 ACT 可消费的 observe 反馈。

## 入口

- workflow：`workflow.lgwf`
- 父级调用：`04_implement_steps_react/workflow.lgwf` 的 `OBSERVE WORKFLOW observe_audit`

## 输入

- `.lgwf/implementation_context.json`
- `.lgwf/implementation_result.json`
- `.lgwf/scaffold_package_result.json`
- `.lgwf/step_designs.json`
- 可选上一轮 `.lgwf/implementation_audit_result.json` 和 `.lgwf/implementation_observe.json`

## 输出

- `.lgwf/implementation_audit_result.json`
- `.lgwf/implementation_observe.json`
- `state.lgwf_wf_create.implementation_audit_result`
- `state.lgwf_wf_create.implementation_observe_result`

## 状态边界

本流程只读目标 package 和 workspace 输入，不修复、不复制、不格式化目标文件。所有运行状态写回当前 run 的 `.lgwf/`。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests -p test_audit_created_package.py
```

## 禁止事项

- 不把脚本 audit 的失败结果改写为通过。
- 不删除 `checks`、`audit`、`failures` 等关键字段。
- 不运行自动修复或注册命令。
