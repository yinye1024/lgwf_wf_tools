请审阅最终摘要草稿，并提交交付决策。

要求：

- 仅接受 JSON object。
- `decision` 只能是 `approve`、`revise` 或 `reject`。
- `comment` 用中文说明原因。
- 若选择 `revise`，请在 `changes` 数组中列出需要补充的点。

`approve` 表示接受当前 Markdown 草稿并进入最终整理；`revise` 表示继续在本阶段内修订；`reject` 表示当前 run 不应继续交付。
