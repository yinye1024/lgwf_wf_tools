# Prompt Repair Spec

`lgwf_wf_prompt_fix` 只负责 ReAct 编排和产物流转。prompt 验收、修复方案、修复执行和复核都必须由对应 Codex slot 按当前 Codex 环境中已安装的 `$lgwf-client-assist` 执行。

入口节点 `check_lgwf_client_assist` 已经负责检测 `lgwf-client-assist` 是否存在。ReAct slot 不允许写死本机路径，不允许自行使用备用路径；如果无法使用 `$lgwf-client-assist`，直接停止并报告依赖缺失。

每个 Codex slot 都必须使用 `$lgwf-client-assist`，按它的 prompt-assist 路由读取对应 reference。`lgwf_wf_prompt_fix` 不复制、不维护 prompt 规范。

中间产物统一写入 `.lgwf/prompt_acceptance/`。只允许按修复计划修改目标 workflow A package 内相关 prompt/source 文件。
