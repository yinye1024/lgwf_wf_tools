# Git Commit 阶段契约

本阶段只读取第四阶段产出的提交计划，并执行或跳过 Git 写操作。

## 输入

- `.lgwf/commit_plan.json`
- `.lgwf/delivery_decision.json`
- `.lgwf/git_context_snapshot.json`

## 输出

- `.lgwf/commit_action_result.json`
- `git_diff_brief.commit_action_result`
- `git_diff_brief.execute_commit_action_result`

## 边界

- 默认 `commit_action=none`，不执行 Git 写操作。
- `stage` 和 `commit` 只能使用提交计划中的 `repo_path` 和 `relative_scope`。
- 不支持 push、amend、分支切换或任意 pathspec。
