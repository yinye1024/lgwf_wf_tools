# repo-context-pack

`repo-context-pack` 是一个内置 LGWF workflow package，用于把目标仓库整理成可复用的上下文包。它坚持两条硬约束：

- 目标仓库只做只读、确定性 Python 扫描
- 运行期不使用 Codex prompt 直接遍历或分析目标仓库

## 适用场景

- 为代码评审、迁移分析、修复规划准备仓库上下文
- 需要稳定抽取入口文件、模块映射、命令线索与风险提示
- 需要同时生成机器可消费 JSON 和面向人的 Markdown 摘要

## 入口

- workflow 入口：`wf/workflow.lgwf`
- 启动契约：`entry_contract.json`
- 产物契约：`wf/artifact_contracts.json`

## 阶段概览

1. `01_entry_scope_resolution`
   规范化请求、解析默认输出目录、检查路径是否满足只读边界。
2. `02_target_context_inventory`
   扫描目录和文件，提取入口、模块关系、命令线索、风险标记与截断信息。
3. `03_context_pack_rendering`
   根据盘点结果生成 Markdown、JSON 与产物索引。
4. `04_workflow_summary_handoff`
   检查产物完整性，生成最终摘要并输出 handoff 信息。

## 最小输入示例

```json
{
  "request": {
    "target_root": "skills/repo-context-pack",
    "target_dirs": [
      "wf",
      "tests"
    ],
    "target_files": [
      "README.md"
    ],
    "output_dir": "artifacts/repo-context-pack",
    "consumer_goal": "为后续代码审阅准备仓库上下文包"
  }
}
```

## 关键输出

- `repo_context_pack_request.json`
- `context_inventory.json`
- `context_pack_generation.json`
- `repo_context_pack_summary.json`

上述文件名和顺序是固定契约；实际落位目录由 `request.output_dir` 决定。

## 约束

- 所有输入路径和产物路径都必须使用相对路径
- 不允许绝对路径、盘符路径、URL 或 `..`
- 目标 package 根目录不写 `.lgwf`
- 根 package profile 为 `internal_workflow_package`，因此不提供根 `SKILL.md`

## 验证

在 package 根目录执行：

```powershell
python -m unittest discover tests
```

并对 `wf/workflow.lgwf` 及各阶段子 workflow 执行 LGWF authoring audit。
