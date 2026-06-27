# Prompt Repair Spec

`lgwf_wf_prompt_fix` 只负责 ReAct 编排和产物流转。prompt 验收、修复方案、修复执行和复核都必须由对应 Codex slot 按 facade 内置 `vendor/lgwf-client-assist/AGENTS.md` 的规则和 references 执行。

入口节点 `check_lgwf_client_assist` 已经负责检测 bundled client 是否存在。ReAct slot 不允许写死本机路径，不允许自行使用备用路径；如果无法读取 bundled client 的 `AGENTS.md` 或 references，直接停止并报告依赖缺失。

每个 Codex slot 都必须按 bundled client 的 prompt-assist 路由读取对应 reference。`lgwf_wf_prompt_fix` 不复制、不维护 prompt 规范。

中间产物统一写入 `.lgwf/prompt_acceptance/`。只允许按修复计划修改目标 workflow A package 内相关 prompt/source 文件。
