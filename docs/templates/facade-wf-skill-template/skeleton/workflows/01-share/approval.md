# Approval 规则

`waiting_human` 不是完成状态。

- 如果是 approval 或 review，在当前对话确认并提交。
- 如果是 agent loop 控制状态但没有 human request，汇报原因、证据和 artifact 路径，等待用户决定。
- 只提交用户明确确认的 approval value。
- `approve` 是纯决策，不携带业务 JSON。
- 只有 `review revise` 需要提交完整业务 value。

## 人工确认展示模板

所有需要用户确认的 `approval`、`review`、`human_choice`、`waiting_human` 和子 workflow 代理确认，都必须先按以下 Markdown 模板展示，再等待用户明确回复。

```markdown
**需要确认：<确认标题>**

- 当前状态：<workflow 状态、节点或 request_id>
- 确认原因：<为什么必须由用户决定>
- 影响范围：<会读取、修改、运行或跳过的对象>
- 待确认内容：<来自 request/context 的摘要；保留关键 JSON 字段、选项和默认值>
- 可选决策：<approve/reject/revise/run/skip/auto/stop 或 workflow 给出的原始 options>
- 提交值：`<approve/reject 只提交决策；revise 展示将提交的完整 JSON 摘要>`
- 相关产物：<artifact、report、work_dir 或 evidence 路径；没有则写“无”>
- 后续动作：<用户确认后会执行什么；拒绝或修订后会发生什么>
```

不得只用一句话询问“是否确认”。
