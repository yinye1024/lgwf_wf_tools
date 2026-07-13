# scaffold_package

## 职责

根据 `.lgwf/create_requirements.json` 和 `.lgwf/business_flow.json` 生成确定性 `scaffold_plan`，为后续步骤设计和实现阶段提供目标 package 的目录、文件和阶段 manifest。

## 输入

- `.lgwf/create_requirements.json`
- `.lgwf/business_flow.json`
- `resources/scaffold_package_template.json`
- `resources/scaffold_template_spec.md`
- `resources/scaffold_result_contract.md`

## 输出

- `state.lgwf_wf_create.scaffold_package_result`

## 产物

- `.lgwf/scaffold_package_result.json`

## 验证

- `python -m unittest tests.test_scaffold_package_rules`
- `python -m unittest tests.test_runtime_mirror_paths`
- `python -m unittest tests.test_scaffold_current_structure`

## 禁止事项

- 不自由设计业务阶段，只按已确认的业务流和模板生成计划。
- 不修改 `.lgwf/business_flow.json` 或 `.lgwf/create_requirements.json`。
- 不向目标 package 根目录写入 `.lgwf`、`.tmp`、`__pycache__` 或运行状态文件。
- 不创建目标 package 实体文件；这里只生成脚手架计划。
