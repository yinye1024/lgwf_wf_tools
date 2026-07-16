# scaffold_result 契约

`scaffold_package` 的输出是确定性 `scaffold_result`，用于说明目标 package 后续将如何由 `03_materialize_scaffold` 落盘，并供 `04_main_agent_handoff` 交给主 agent 继续完善；本阶段不创建或覆盖目标 package 真实文件。

`scaffold_result` 必须能证明目标 package 遵循 `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md` 中的 workflow 模块化创建指引：workflow package、子 workflow、复杂 step、运行状态和验证入口都有明确边界。

## 最小结构

`scaffold_result` 至少应包含以下字段：

```json
{
  "scaffold_plan": {
    "workflow_name": "目标 workflow 名称",
    "target_package_root": "目标 package 相对目录",
    "package_profile": "internal_workflow_package",
    "template": {
      "template_id": "workflow_packaged_skill",
      "template_version": 1,
      "description": "外层 package 包住内层 wf/ workflow root 的脚手架模板",
      "profile_description": "当前 profile 的用途说明"
    },
    "rules": {
      "path_policy": ["只使用相对路径", "禁止绝对路径", "禁止 `..`"],
      "state_boundary": [
        "脚手架只生成目标 package 框架计划",
        "不创建或覆盖目标 package 真实文件",
        "不向目标 package 根目录写入 `.lgwf`",
        "运行状态边界仍归 `ws/.lgwf`"
      ]
    },
    "create_dirs": ["将要创建的目录"],
    "create_files": ["将要创建的文件"],
    "placeholders": {
      "wf": "唯一 workflow package root；真实入口为 wf/workflow.lgwf",
      "wf/<stage>": "第一层子 workflow 目录；必须自包含，不得再嵌套子 workflow"
    },
    "derived_from_business_flow": [
      {
        "stage_id": "来源业务阶段 ID",
        "key_nodes": ["来源节点命名"],
        "human_approval": false
      }
    ]
  }
}
```

## 规则说明

- `target_package_root` 只允许使用相对路径，禁止绝对路径、盘符路径和 `..`。
- `package_profile=internal_workflow_package` 时，`create_files` 必须包含 `AGENTS.md` 与 `wf/workflow.lgwf`，不得包含根 `SKILL.md`。
- `package_profile=skill_wrapped_workflow` 时，`create_files` 必须包含根 `SKILL.md`；该文件只作为 Codex skill 入口和路由封装，不承载内部 workflow 细节。
- 已确认需求中显式列出的 package 源文件，例如 `scripts/*.py`、`tests/*.py`、`wf/shared/scripts/*.py`，必须进入 `create_files`；这些文件后续由 `03_materialize_scaffold` 创建最小初稿，再由主 agent 替换为真实实现。
- `create_dirs` 与 `create_files` 只描述目标 package 框架，不描述运行状态文件。
- `scaffold_package` 不创建或覆盖目标 package 实体文件；真实文件只由 `03_materialize_scaffold` 在目标 package 内受控落盘。
- 运行状态边界固定在 `ws/.lgwf`，不得把 `.lgwf` 写入目标 package 根目录。
- `derived_from_business_flow` 用于证明脚手架计划与业务流转 proposal 的阶段和节点命名保持可追踪关系。
- workflow 拓扑只允许两层：`wf/workflow.lgwf` 作为主编排，`wf/<stage>/workflow.lgwf` 作为第一层子 workflow。
- 子 workflow 目录必须自包含该阶段的 `workflow.lgwf`、`artifact_contracts.json` 和阶段私有的 `agents/`、`scripts/`、`resources/`；`create_files` 不得包含 `wf/<stage>/<substage>/workflow.lgwf`。
- 每个 `wf/<stage>/artifact_contracts.json` 必须进入 `create_files`，用于支撑 `lgwf.py audit wf/<stage>/workflow.lgwf` 单独审计时识别本阶段的 bootstrap inputs 和 final outputs。
- 共享 Python helper 可放入 `wf/shared/scripts/`；prompt、approval prompt 和 spec 必须留在对应 `wf/<stage>/` 目录内。

## 当前 run 边界

- 当前 run 只验证 `scaffold_result` 契约、脚手架规则和最小验证入口。
- 当前 run 只有在 `confirm_business_flow` 为 `approve` 时才固化 `.lgwf/business_flow.json`。
- 当前 run 不要求真实执行目标 package 的端到端创建。
