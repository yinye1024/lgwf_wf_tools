# 设计根 workflow 与阶段子 workflow

## 步骤标识

- `step_slug`: `design-root-and-stage-workflows`
- 对齐阶段：`01_entry_scope_resolution`、`02_target_context_inventory`、`03_context_pack_rendering`、`04_workflow_summary_handoff`

## 目标

定义两层拓扑的 workflow 初稿：根 `wf/workflow.lgwf` 只做薄编排，下沉四个第一层阶段子 workflow 负责具体实现，不创建孙级 workflow，不引入人工确认节点。

## 输入

- `stage_manifest` 中固定的 `stage_dir`、`workflow_ref` 和 `key_nodes`
- 业务流确认后的四阶段顺序与交接文件名
- `artifact_contracts.json` 对关键运行产物和报告的声明边界

## 输出

- `wf/workflow.lgwf`
- `wf/artifact_contracts.json`
- `wf/01_entry_scope_resolution/workflow.lgwf`
- `wf/02_target_context_inventory/workflow.lgwf`
- `wf/03_context_pack_rendering/workflow.lgwf`
- `wf/04_workflow_summary_handoff/workflow.lgwf`
- `wf/01_entry_scope_resolution/scripts/run.py`
- `wf/02_target_context_inventory/scripts/run.py`
- `wf/03_context_pack_rendering/scripts/run.py`
- `wf/04_workflow_summary_handoff/scripts/run.py`

## 固定交接顺序

1. `01_entry_scope_resolution` 产出 `.lgwf/repo_context_pack_request.json`
2. `02_target_context_inventory` 消费请求并产出 `.lgwf/context_inventory.json`
3. `03_context_pack_rendering` 消费请求和 inventory，产出 `.lgwf/context_pack_generation.json`
4. `04_workflow_summary_handoff` 消费前三阶段结果并产出 `.lgwf/repo_context_pack_summary.json`

## 确认要点

- 根 workflow 只保留顺序编排和阶段级 contract，不在根节点承载扫描、渲染或摘要细节
- 阶段目录必须使用真实 `stage_dir`，不能把业务 `stage_id` 重新推导成其他目录名
- `artifact_contracts.json` 只描述关键业务产物和报告，不夹带控制面临时状态

## 实现建议

- 每个 `wf/<stage>/` 目录自包含 `workflow.lgwf`、`agents/`、`scripts/`、`resources/`
- 阶段内部如存在复杂逻辑，应在各自 `workflow.lgwf` 中用 `PY`、`CODEX`、`ROUTE` 等节点表达，不新增孙级 workflow
- 根 workflow 的 contract 仅声明阶段间必须读写的 `.lgwf/*.json` 交接文件，避免过早绑定产物细节
- 在设计说明中显式记录当前漂移：`stage_manifest` 期望的步骤文档命名与本轮 staging 输出的设计文档命名不一致，后续需要收敛

## 验收

- 仅存在 `wf/workflow.lgwf` 与 `wf/<stage>/workflow.lgwf` 两级 workflow 文件
- 不存在 `wf/<stage>/<substage>/workflow.lgwf`
- 所有 workflow 引用路径都使用 package 内相对路径，不包含绝对路径、盘符路径或 `..`

## 禁止事项

- 不要在根 workflow 中加入人工确认、修复循环或跨阶段细节实现
- 不要把 `stage_id` 当作目录名覆盖 `stage_dir`
- 不要在 `artifact_contracts.json` 中声明 `.lgwf` 控制面临时状态
