# confirm_scope 步骤说明

## 目标

确认 `01_collect_targets` 生成的授权目标范围，防止 workflow 在未确认的目录或文件上进入 `FOREACH` 修复。

## 输入

- `state.wf_dsl_upgrade.targets`
- `ws/.lgwf/target_manifest.json`
- `ws/.lgwf/target_scope_validation.json`

## 输出

- `state.wf_dsl_upgrade.scope_confirmation_context`
- `state.wf_dsl_upgrade.scope_approval`
- `state.wf_dsl_upgrade.scope_route`
- `ws/.lgwf/scope_confirmation_context.json`
- `ws/.lgwf/scope_approval.json`

## 执行规则

- 使用 `APPROVAL`，只允许 `approve` / `reject`。
- `APPROVAL` 在 `approve` 时持久化的是已批准的 scope context，不是 `{ "decision": "approve" }`。
- 路由脚本只读取 `RESULT state.wf_dsl_upgrade.confirm_scope_result` 中的 decision；业务 context 不作为控制分支的 decision 来源。
- `approve` 且 scope validation 通过时，根 workflow 路由到 `FOREACH upgrade_each`。
- `reject` 或 scope validation 失败时，根 workflow 直接进入 summary。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-dsl-upgrade\tests
```
