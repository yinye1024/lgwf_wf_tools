请审阅当前请求范围 JSON，并提交确认决策。

要求：

- 仅接受 JSON object，作为 approval 的 `value` 提交。
- `approval` 只能是 `approve`、`revise` 或 `reject`。
- `changes` 使用数组，列出需要补充或修正的点。
- `comment` 用中文说明理由。

当输入已经满足“仓库目录 + 工作区 git diff + 最近一次提交信息”的最小范围时，可直接 `approve`。如果还需要补充分支名、提交范围或输出位置，请使用 `revise` 明确列出。若当前请求整体不成立，使用 `reject`。
