# 模块 Contract 运行期摘要

本文件是 `workflows/01-share/module-contract.md` 中与 `wf-create` 生成目标 workflow package 直接相关的运行期摘要，用于 `enrich_contracts_react` 在隔离运行目录中补齐目标包入口文档。

## lgwf_workflow_package 必备说明

目标 workflow package 的入口文档必须说明以下内容：

- 模块定位：说明该 workflow 是否是 facade 内部 workflow、普通 skill 内嵌 workflow，且不得误注册为独立 Codex skill。
- 入口：声明 registry id、`workflow_lgwf`、`work_dir`、`entry_contract.json` 和启动命令；普通 skill 内嵌 workflow 声明 `wf/workflow.lgwf`。
- 依赖：声明 bundled client、共享规则、上下游 workflow 和目标 package 输入依赖。
- 状态边界：运行状态只写入声明的 work dir 下 `.lgwf/`；workflow source root 与 work dir 必须分离。
- 产物：列出主要 `.lgwf/` 文件、报告目录和 handoff payload。
- 验证：提供 `lgwf.py audit` 和对应测试命令；只改文档时至少确认 UTF-8 和路径示例。
- 禁止事项：资源路径必须相对，禁止绝对路径和 `..`；不得在子 workflow 下继续创建孙级 `workflow.lgwf`，不得绕过 approval。

## 适用边界

- 目标包可以引用共享规则，但自己的 `AGENTS.md` 或 `README.md` 仍要写清楚具体入口、依赖、状态边界和验证命令。
- 自包含不表示复制 runtime、vendor 或仓库级共享规则；自包含表示目标包文档、运行目录、产物和验证方式自解释。
- Contract 补强只补目标包文档契约，不新增业务能力，不自动接入 facade registry。
