# implement_one_unit

## 职责

执行一个 implementation unit：准备当前 unit context、约束 Codex 只写 staging 文件，并把 staging 结果发布到目标 package。

该目录是 `implement_units` 内部的孙级 workflow。它独立存在是因为单 unit 有自己的输入、输出、schema 注入、staging 目录、发布脚本和失败恢复边界。

## 入口

- workflow：`workflow.lgwf`
- 父级调用：`01_implement_units/workflow.lgwf` 的 `FOREACH implement_each_unit`

## 输入

- `state.lgwf_wf_create.current_implementation_unit`
- `.lgwf/implementation_context.json`
- `.lgwf/current_implementation_unit_context.json`
- 本地 `resources/codex_output_schemas.json`

## 输出

- `.lgwf/current_implementation_unit_context.json`
- `.lgwf/current_implementation_unit_result.json`
- `.lgwf/implementation_stage/<unit_id>/`
- `state.lgwf_wf_create.current_implementation_unit_result`

## 状态边界

Codex 只能修改 `.lgwf/current_implementation_unit_context.json` 中 `workspace_output_files` 列出的 staging 文件。最终目标 package 的写入由 `scripts/publish_current_implementation_unit_result.py` 负责。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-create\tests -p test_implementation_units.py
```

## 禁止事项

- 不直接写 `target_package_abs`。
- 不读取其他 unit 的 staging 文件。
- 不递归搜索 `.lgwf`、checkpoint、Codex stdout、human request、测试文件或宿主仓库样例来推导 schema。
- 不修改 `workspace_output_files` 清单之外的文件。
