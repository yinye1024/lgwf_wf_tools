# Approval 规则

`waiting_human` 不是完成状态。

- 如果是 `flow.human_approval`，按 vendor main-agent ask flow 在当前对话确认并提交。
- 如果是 `AGENT_LOOP` 控制状态但没有 human request，汇报 loop reason、evidence 和 artifact 路径，等待用户决定。
- 只提交用户明确确认的 approval value。
- `approve` 是纯决策，不得携带 `--value-json`。节点应自行固化已经展示的 proposal；如果需要替换业务对象，必须走 `revise`。
- 提交 `review revise` value 时，优先使用 `scripts/safe_approval_submit.py`，通过 `--value-file` 或 `--value-json-base64` 传入 UTF-8 JSON；脚本会转换成 ASCII-only `--value-json` argv 后调用 facade，避免 PowerShell 参数层把中文写成 `????`。
- 只有 `review revise` payload 是纯 ASCII 且结构简单时，才可直接调用 `review submit --value-json`。

## 人工确认展示模板

所有需要用户确认的 `approval`、`review`、`human_choice`、`waiting_human` 和子 workflow 代理确认，都必须先按以下 Markdown 模板展示，再等待用户明确回复。不得只用一句话询问“是否确认”，不得省略 workflow 原始 request/context 中影响决策的关键字段。

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

模板约束：

- `确认标题` 优先使用 workflow request 的 `title` 或 prompt 标题；没有时用当前节点名和 request 类型生成。
- `待确认内容` 必须覆盖原始 context 中的目标路径、修改范围、风险、跳过影响、验收口径、候选选项和已生成 artifact。原始 context 过长时可以摘要，但不能丢失会影响选择的字段。
- `可选决策` 必须使用 workflow 原始 options 或该节点契约允许的值；不要自行新增分支。
- `提交值` 必须让用户能看出最终会提交什么。`approve` 不得提交业务 value；`revise` 涉及中文或复杂嵌套时，先准备 UTF-8 no BOM value 文件，再用安全提交脚本。
- 子 workflow approval 不能被父 workflow 的 `auto`、默认值或历史选择绕过；必须展示子 workflow 原始确认上下文并等待明确确认。
