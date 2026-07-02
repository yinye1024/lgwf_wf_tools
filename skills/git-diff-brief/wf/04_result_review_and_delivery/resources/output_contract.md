# 最终输出契约

第四阶段负责展示、确认和整理最终结果，不重新生成 Git 事实。

## 目标字段

- `final_change_brief_markdown`
- `delivery_decision`
- `commit_message_suggestion`
- `commit_message_suggestion_zh`
- `commit_message_rationale`
- `commit_plan`
- `commit_action_result`
- `run_artifact_index`

## 待确认项

- 是否默认落盘 Markdown 文件
- 默认文件命名策略
- `revise` 时是否原地重写草稿，还是保留多版本索引
- 空 diff 的最终对外文案
- 是否在本次人工确认中选择 `stage` 或 `commit`

## 边界

- 运行痕迹只允许写入 work dir 下的 `.lgwf`
- 不向目标 package 根目录写 `.lgwf`
- 本阶段内部自行处理 `approve` / `revise` / `reject`
- `finalize_output` 只整理最终结果和提交计划
- `execute_commit_action` 是唯一允许执行 `git add` / `git commit` 的节点
- 默认 `commit_action=none`，不执行 Git 写操作
- `stage` / `commit` 只能使用 `.lgwf/git_context_snapshot.json` 中的 `repo_path` 和 `relative_scope`
- `commit_message_suggestion` 是英文 Conventional Commits 版本，默认用于真实 `git commit -m`
- `commit_message_suggestion_zh` 是中文展示版本，只用于人工理解和确认
