# 是否运行 wf-prompt-upgrade

即将运行：`wf-prompt-upgrade`

作用：提升 prompt 的角色职责、决策标准、失败模式、上下游协作契约和可验收质量指标。

可能影响：会在用户确认升级方案后修改目标 workflow package 内的 prompt/source 文件。

跳过影响：只保留已有基础修复，不做更高层的 prompt 质量升级。

请选择并提交 JSON：`{"decision":"run|skip|auto|stop","reason":"..."}`。

`stop` 会让当前子 workflow 直接 `FAIL_ALL` 并终止整个 post-fix 运行。
