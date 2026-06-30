# Git 上下文契约

第二阶段输出必须为下游摘要阶段可直接消费的结构化事实。

## 目标字段

- `git_diff_snapshot`
  - `diff_text`
  - `diff_name_only`
  - `status_lines`
- `latest_commit_context`
  - `commit_hash`
  - `subject`
  - `body`
- `changed_files_index`
  - `files`
  - `count`
- `git_collection_log`
  - `repo_path`
  - `status`
  - `warnings`

## 设计边界

- Git 命令执行和结构化解析由 `scripts/collect_git_context.py` 负责。
- 摘要阶段只能读取这里定义的输出，不应再次执行 Git 命令。
- 空 diff、无提交历史和超大 diff 仅记录风险，不在本阶段擅自做最终产品决策。
