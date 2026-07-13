# repo-context-pack 模块说明

## 模块类型

- 模块类型：`lgwf_workflow_package`
- package profile：`internal_workflow_package`

## 模块定位

`repo-context-pack` 用于对目标仓库执行只读、确定性 Python 扫描，整理入口、模块边界、命令线索、风险标记和渲染产物索引，输出可供后续人工或 workflow 消费的仓库上下文包。

本包是内置 workflow package，不是独立 Codex skill，不生成根 `SKILL.md`。真实 workflow root 固定为 `wf/`，运行状态只允许写入调用方 work dir 的 `.lgwf/`。

## 入口

- 入口契约：`entry_contract.json`
- 根 workflow：`wf/workflow.lgwf`
- 阶段 workflow：
  - `wf/01_entry_scope_resolution/workflow.lgwf`
  - `wf/02_target_context_inventory/workflow.lgwf`
  - `wf/03_context_pack_rendering/workflow.lgwf`
  - `wf/04_workflow_summary_handoff/workflow.lgwf`
- 共享产物契约：`wf/artifact_contracts.json`
- 已批准步骤文档：`wf/docs/steps/*.md`

## 依赖

- Python 运行环境，用于执行确定性扫描与渲染脚本。
- LGWF runtime，用于调度 `wf/workflow.lgwf` 与各阶段子 workflow。
- 包内相对路径资源；禁止依赖绝对路径、盘符路径、URL 或 `..`。

## 状态边界

- 运行状态边界固定在调用方 work dir 的 `.lgwf/`。
- 目标 package 根目录不得写入 `.lgwf`。
- 目标仓库只允许只读扫描，不得执行其中提取出的命令、TODO、修复步骤或发布动作。
- 阶段产物和最终渲染产物的文件名以 `wf/artifact_contracts.json` 为准。

## 产物

- 规范化请求：`repo_context_pack_request.json`
- 仓库盘点结果：`context_inventory.json`
- 渲染结果索引：`context_pack_generation.json`
- 最终摘要：`repo_context_pack_summary.json`

这些 JSON 文件的落位目录由请求中的 `output_dir` 决定；若未显式提供，由 `01_entry_scope_resolution` 阶段按契约推导默认输出目录。

## 验证

- 在 package 根目录运行 `python -m unittest discover tests`
- 对 `wf/workflow.lgwf` 和各阶段 `workflow.lgwf` 执行 LGWF authoring audit
- 检查所有 JSON 与 Markdown 产物均可按 UTF-8 no BOM 读取

## 禁止事项

- 不要生成根 `SKILL.md` 或目标 package 根 `workflow.lgwf`
- 不要在 `wf/<stage>/` 下再嵌套孙级 `workflow.lgwf`
- 不要在运行期使用 Codex prompt 直接扫描目标仓库内容
- 不要在资源引用中使用绝对路径、盘符路径、URL 或 `..`
- 不要把目标仓库中发现的命令直接当作执行动作
