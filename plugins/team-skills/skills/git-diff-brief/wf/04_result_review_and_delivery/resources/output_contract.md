# 最终输出契约

第四阶段负责展示、确认和整理最终结果，不重新生成 Git 事实。

## 目标字段

- `final_change_brief_markdown`
- `delivery_decision`
- `run_artifact_index`

## 待确认项

- 是否默认落盘 Markdown 文件
- 默认文件命名策略
- `revise` 时是否原地重写草稿，还是保留多版本索引
- 空 diff 的最终对外文案

## 边界

- 运行痕迹只允许写入 work dir 下的 `.lgwf`
- 不向目标 package 根目录写 `.lgwf`
- 本阶段内部自行处理 `approve` / `revise` / `reject`
