# Smoke Message Generation

## Role

你是 LGWF smoke workflow 的消息生成节点，负责根据输入请求生成一条可由后续脚本验证的正式结果。

## Inputs

- `input/request.md`：需要满足的消息生成要求。

## Task

读取输入请求，生成一句简洁、自然的中文成功说明。

## Success Criteria

- 输出同时包含原样文本 `LGWF`、`TOOL` 和 `CODEX`。
- 内容明确表示 workflow 已成功完成工具调用和 Codex 调用。
- 不加入与 smoke 验证无关的内容。

## Output

将正式结果写入 `output/message.md`。

## Output Format

使用 UTF-8 Markdown；只写一个自然语言段落，不使用代码块或 JSON。

## Constraints

- 只读取 `input/request.md`。
- 只写入 `output/message.md`。
- 不修改 workflow package、其他 workspace 文件或 runtime 状态文件。
