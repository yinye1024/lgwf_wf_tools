# lgwf_wf_prompt_upgrade

`lgwf_wf_prompt_upgrade` 面向 prompt 设计升级，不做基础规范检查。推荐先运行 `lgwf-wf-prompt-fix`，确认 prompt 满足基础格式、引用和输出契约规范后，再运行本 workflow。

核心流程：

1. 确认目标 workflow。
2. 盘点目标 workflow package 内被 `PROMPT` / `PROMPT_REF` 引用的 prompt。
3. 生成 prompt 设计分析和升级方案。
4. 人工确认升级范围。
5. 按确认方案应用升级并复核。
6. 输出 summary。

