# materialize_scaffold 阶段

本阶段把 `.lgwf/scaffold_package_result.json` 中的 `scaffold_plan` 转换为真实目标 workflow package 文件。它只做确定性 scaffold 落盘，不做步骤设计、不调用 Codex、不覆盖已有非空文件。

## 输入

- `.lgwf/create_requirements.json`
- `.lgwf/business_flow.json`
- `.lgwf/scaffold_package_result.json`

## 输出

- `.lgwf/materialize_scaffold_result.json`
- `state.lgwf_wf_create_fast.materialize_scaffold_result`
- 目标 package 中的最小可编辑 scaffold 文件

## 状态边界

- 运行状态仍写入当前 work dir 的 `.lgwf/`。
- 目标 package 不得写入 `.lgwf/`。
- `target_package_root` 可以是绝对路径或相对路径；相对路径按当前 run 的 work dir 解析。

## 验证

```powershell
python -m unittest skills\lgwf-wf-tools\workflows\wf-create-fast\tests\test_materialize_scaffold.py
```

## 禁止事项

- 不得覆盖已有非空文件。
- 不得生成 `step_designs.json`。
- 不得自动执行目标 workflow。
