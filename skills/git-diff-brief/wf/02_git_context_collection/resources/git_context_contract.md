# Git 上下文契约

第二阶段输出必须为下游摘要阶段可直接消费的结构化事实。

## 目标字段

- `git_diff_snapshot`
  - `diff_text`
  - `diff_stat`
  - `diff_name_only`
  - `status_lines`
- `git_diff_compact`
  - `diff_stat`
  - `diff_name_only`
  - `status_lines`
  - `directory_groups`
  - `diff_snippets`
- `context_budget`
  - `max_total_diff_chars`
  - `max_file_diff_chars`
  - `original_diff_chars`
  - `retained_diff_chars`
  - `truncated_files`
  - `heavy_files`
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
- 完整 `git_diff_snapshot.diff_text` 只用于追溯和提交阶段，不进入 Codex 摘要节点。
- Codex 审计和摘要阶段读取 `.lgwf/git_context_compact.json`，不应再次执行 Git 命令。
- 空 diff、无提交历史和超大 diff 仅记录风险，不在本阶段擅自做最终产品决策。
