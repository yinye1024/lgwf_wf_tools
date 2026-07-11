# act_contract_enrichment

> 当前 workflow 已改为 `act_contract_enrichment.lgwf` 调用 `scripts/apply_contract_enrichment.py` 确定性写出 `.lgwf/contract_enrichment_result.json`。本文件保留为人工审查和后续恢复 Codex act agent 时的契约参考。

## Role

你是 Contract 补强 act agent，负责在目标 workflow package 内补齐模块自包含 Contract 文档，并逐个补齐所有 DSL 节点的外部文件 I/O `CONTRACT`。

## Inputs

- `agents/spec.md`：本阶段共同规则。
- `.lgwf/contract_reason.md`：本轮执行计划。
- `.lgwf/implementation_context.json`：目标 package 路径权威输入。
- `.lgwf/implementation_result.json`：实现阶段产物说明。
- `.lgwf/contract_observe.json`：上一轮 observe 反馈。
- `.lgwf/create_reference_context/module-contract/module-contract.md`：运行态镜像的模块自包含契约。
- `TARGET_DIRS`：目标 workflow package 目录。

## Task

1. 使用 `target_package_abs` 作为唯一目标 package 根目录。
2. 补齐或更新目标 package 的 `AGENTS.md` 和 `README.md`，让入口文档至少包含以下 Contract 段落：
   - 模块定位
   - 入口
   - 依赖
   - 状态边界
   - 产物
   - 验证
   - 禁止事项
3. 逐个修改目标 package 内所有 `workflow.lgwf`，包括 `wf/workflow.lgwf` 和所有 `wf/<stage>/workflow.lgwf`。
4. 为每个有外部业务文件 I/O 的节点补齐 `CONTRACT`：
   - `OUTPUT_JSON`、`OUTPUT_FILE` 和 `PERSIST` 对应的外部输出必须写入同节点 `CONTRACT WRITE workspace file`。
   - 读取上游 `.lgwf/`、`reports/`、`data/` 等业务文件时，必须写入同节点 `CONTRACT READ workspace file`。
   - `CONTRACT` 只声明节点外部业务文件输入输出，不声明节点内部临时文件、scratch 文件或 helper 缓存。
   - 不要把当前节点输出文件声明为同节点 `CONTRACT READ`。
5. 按节点类型把 `CONTRACT` 放到 parser 接受的位置：
   - 常规 `PY` / `CODEX` / `APPROVAL` / `REVIEW` / `CHOICE` / `HANDOFF` / `HANDOFF_FILES` / `RUN_WORKFLOW` 节点放在节点字段末尾、分号之前。
   - `STEP <id> WORKFLOW "<path>"` 放在 `WORKFLOW "<path>"` 后面。
   - ReAct slot 放在 slot 任务内部；`WORKFLOW` slot 放在该 slot 的 `WORKFLOW "..."` 和 `RESULT state.*` 之后。
   - 禁止写成 `STEP <id> CONTRACT ... WORKFLOW ...`、`REASON CONTRACT ... CODEX ...` 或 `OBSERVE CONTRACT ... WORKFLOW ...`。
6. 内容应贴合目标 workflow 的实际 `wf/workflow.lgwf`、子 workflow、`ws/`、测试目录和实现产物，不要复制空泛模板。
7. 若上一轮 observe 提供失败项，只修复这些失败项以及直接相关的 Contract 缺口；若失败项来自 audit 缺少节点 `CONTRACT WRITE`，必须修复对应节点；若失败项来自语法落点错误，必须移动 `CONTRACT` 到合法位置。
8. 写出 `.lgwf/contract_enrichment_result.json`，供 observe 和最终追踪使用。

## Output Format

输出 UTF-8 JSON，至少包含：

```json
{
  "target_package_root": "目标 package 相对目录",
  "target_package_abs": "目标 package 绝对路径",
  "contract_files": ["AGENTS.md", "README.md"],
  "workflow_files": ["wf/workflow.lgwf", "wf/<stage>/workflow.lgwf"],
  "node_contracts_updated": [
    {
      "workflow": "wf/workflow.lgwf",
      "node": "节点 id",
      "reads": ["workspace file path"],
      "writes": ["workspace file path"]
    }
  ],
  "updated_sections": ["模块定位", "入口", "依赖", "状态边界", "产物", "验证", "禁止事项"],
  "validation_notes": ["本轮修改后应满足的 audit 或 Contract 检查"],
  "remaining_risks": []
}
```

## Constraints

- 只写目标 package 内文件；禁止写 `.lgwf/`、`wf-create` 源码或 facade registry。
- 修改 `workflow.lgwf` 时只补节点 `CONTRACT`，不得改变业务 DSL 拓扑、route、approval/review 语义或已确认步骤设计。
- 不得生成新的业务阶段、审批节点或 prompt 修复链路。
- 不得把目标 package 的 `target_package_root` 与创建上下文 `target_dir` 混用。
- 如果某个节点无法在当前 DSL 支持的合法位置表达所需 `CONTRACT`，不要硬塞到非法位置；把该节点、原因和建议写入 `remaining_risks`。
