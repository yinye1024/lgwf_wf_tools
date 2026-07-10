# 分析当前 DSL audit diagnostics

请分析当前目标 `.lgwf` 的 audit 结果，输出诊断归因和修复判断。本 slot 不修改文件，只说明下一步是否可以安全做最小修复。

关注：

- diagnostics 的 code、message 和 location。
- 当前文件中缺失或位置错误的 `CONTRACT`，以及该诊断是否能从当前文件内证实。
- 最小可行修复，不扩大到无关格式化、批量迁移或重构。
- 如果缺少足够语义上下文，明确说明需要人工处理的原因，后续应让 `finalize_target` 标记 `needs_manual_review`。

不修改文件，不新增文件，不运行额外命令。本 slot 只产出分析结果。
