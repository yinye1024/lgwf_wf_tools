# 请求范围契约

第一阶段只负责规范化输入，不执行 Git 命令。

## 输入边界

- 允许接收仓库目录提示、摘要目标和可选备注。
- 默认摘要范围下限固定为：
  - 工作区 `git diff`
  - 最近一次提交信息

## 输出对象

- `repository_input_context`
  - `repo_hint`
  - `normalized_repo_hint`
  - `path_exists`
- `summary_scope`
  - `baseline`
  - `requested_extensions`
- `scope_confirmation_input`
  - `needs_confirmation`
  - `open_questions`
  - `recommended_decision`

## 禁止事项

- 不向目标 package 根目录写 `.lgwf`
- 不提前决定自定义输出路径
- 不在本阶段读取 Git diff 或提交详情
