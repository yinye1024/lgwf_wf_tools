# scaffold result contract

`scaffold_package.py` 输出的 `scaffold_plan` 至少包含：

- `workflow_name`
- `target_package_root`
- `package_profile`
- `template`
- `rules`
- `create_dirs`
- `create_files`
- `placeholders`
- `derived_from_business_flow`

当前阶段只生成确定性计划对象，不直接落盘最终 package 文件树。
