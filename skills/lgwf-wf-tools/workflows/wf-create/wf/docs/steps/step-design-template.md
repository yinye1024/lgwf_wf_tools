# 步骤设计文档模板

> 用途：作为 `design_steps_react` 输出 `docs/steps/*.md` 时的统一结构模板。

## step_slug

`prepare-package-layout`

## step_name

准备 package 布局

## goal

说明这个步骤要完成的目标、存在原因，以及它为后续 workflow 初稿提供什么价值。

## inputs

- 上游阶段或节点：
- 依赖文件或状态：
- 关键约束：

## outputs

- 预期生成的文件：
- 预期生成的目录：
- 交付给下游的结构片段：

## dependencies

- 前置步骤：
- 依赖节点：
- 需要人工确认的位置：

## implementation_suggestions

- 建议修改或创建哪些 workflow 文件、Markdown、脚本或资源。
- 标明关键命名约定、相对路径约束和 work dir 边界。
- 只给出实现建议，不直接写成完整实现代码。

## acceptance_notes

- 人工审查时应重点核对的字段、边界或风险。
- 若存在待确认假设，在这里显式列出。

## out_of_scope

- `lgwf-wf-prompt-fix` 集成
- `lgwf-wf-tools` 集成
- 自动修复、自动重试或端到端运行保证
