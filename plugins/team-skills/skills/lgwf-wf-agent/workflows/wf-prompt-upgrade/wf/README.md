# lgwf_wf_prompt_upgrade

`lgwf_wf_prompt_upgrade` 面向 prompt 设计升级，不做基础规范检查。推荐先运行 `lgwf-wf-prompt-fix`，确认 prompt 满足基础格式、引用和输出契约规范后，再运行本 workflow。

根 `workflow.lgwf` 只编排 `prepare_target`、`design_upgrade`、`confirm_upgrade`、`apply_upgrade` 和 `summary` 五个阶段。每个阶段的脚本、prompt、approval 和执行细节由对应子 workflow 维护。

核心流程：

1. 确认目标 workflow。
2. 盘点目标 workflow package 内被 `PROMPT` / `PROMPT_REF` 引用的 prompt，包括嵌套 workflow。
3. 生成 prompt 设计分析和升级方案。
4. 人工确认升级范围。
5. 生成 apply plan，并在实际修改前校验文件路径必须属于已批准升级项和允许的 `target_dirs`。
6. 按确认方案应用升级并复核。
7. 输出 summary。
