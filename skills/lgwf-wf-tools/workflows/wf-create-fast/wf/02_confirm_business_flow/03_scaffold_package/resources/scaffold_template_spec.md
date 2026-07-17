# scaffold package 模板规范

本规范定义 `lgwf-wf-create-fast` 生成轻量 workflow scaffold 时必须遵循的 package 结构。它面向 `03_materialize_scaffold`、`04_main_agent_handoff` 和后续接手的主 agent；机器可读模板见 `scaffold_package_template.json`，脚手架输出契约见 `scaffold_result_contract.md`。

## 目标结构

默认生成“外层 package + 内层 workflow root”的结构：

```text
<target-package>/
  AGENTS.md
  README.md
  entry_contract.json
  scripts/
  tests/
  ws/
  wf/
    workflow.lgwf
    artifact_contracts.json
    shared/
      scripts/
    <stage>/
      workflow.lgwf
      artifact_contracts.json
      agents/
      scripts/
      resources/
```

`wf/` 是唯一 workflow package root，真实入口固定为 `wf/workflow.lgwf`。根目录不得再生成可运行的 `workflow.lgwf`。

## package_profile

| profile | 用途 | 根 `SKILL.md` |
| --- | --- | --- |
| `internal_workflow_package` | 可迁移到 `lgwf-wf-tools/workflows/*` 的内部 workflow package | 不生成 |
| `skill_wrapped_workflow` | 包了 `wf/` workflow 的 Codex skill package | 生成 |

当 `package_profile=skill_wrapped_workflow` 时，根 `SKILL.md` 只能作为 skill 入口说明和路由封装，不能承载内部 workflow 的详细运行逻辑。

## 路径规则

- `target_package_root` 可以使用绝对路径或相对路径；相对路径按当前 run 的 work dir 解析。
- resource path、`create_dirs` 和 `create_files` 必须使用包内相对路径。
- 禁止 URL、`..` 和指向 `.lgwf` 的路径；包内 resource path 额外禁止绝对路径和盘符路径。
- 生成文件必须落在目标 package 内。
- `workflow.lgwf` 只能出现在 `wf/workflow.lgwf` 与 `wf/<stage>/workflow.lgwf` 两类位置。
- `ws/` 与 `wf/` 同级，只作为 LGWF work-dir；运行态只能写入 `ws/.lgwf`。

## scaffold_plan 契约

`scaffold_package` 必须根据已确认的 `.lgwf/create_requirements.json`、`.lgwf/business_flow.json` 和 `scaffold_package_template.json` 生成确定性 `scaffold_plan`。

`scaffold_plan` 至少包含：

- `workflow_name`
- `target_package_root`
- `package_profile`
- `template`
- `rules`
- `stage_manifest`
- `create_dirs`
- `create_files`
- `placeholders`
- `derived_from_business_flow`

后续 `03_materialize_scaffold` 必须优先遵循 `scaffold_plan`，不得自行发明与模板冲突的根目录结构。`04_main_agent_handoff` 只把已确认需求、业务流、scaffold plan 和落盘结果交给主 agent。

## 阶段职责

- `define_requirements`：聚合原始意图整理、需求 proposal 和需求确认。
- `design_structure`：聚合业务流 proposal、业务流确认和 scaffold plan。
- `materialize_scaffold`：把 `scaffold_plan.create_dirs/create_files` 落盘成目标 package 的最小可编辑初稿。
- `main_agent_handoff`：把目标 package 和上下文交给主 agent 继续完善。

## 禁止事项

- 不得在目标 package 根目录生成 `workflow.lgwf`。
- 不得生成孙级 workflow，例如 `wf/<stage>/<substage>/workflow.lgwf`。
- 不得把阶段私有 prompt 或资源放到全局目录来绕过子 workflow 自包含边界。
- 不得把 `.lgwf`、`.tmp`、`__pycache__` 写入源码树。
- 不得生成或消费 `.lgwf/step_designs.json`。
- 不得自动启动其他下游 workflow。
