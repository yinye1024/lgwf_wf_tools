# scaffold package 模板规范

本规范定义 `lgwf-wf-create` 生成 workflow 初稿时必须遵循的 package 结构。它面向 `design_steps_react`、`implement_steps_react` 和人工审阅者；机器可读模板见 `scaffold_package_template.json`，脚手架输出契约见 `scaffold_result_contract.md`。

## 目标结构

默认生成“外层 package + 内层 workflow root”的结构：

```text
<target-package>/
  AGENTS.md
  README.md
  scripts/
  tests/
  ws/
  wf/
    workflow.lgwf
    01_confirm_requirements/
      workflow.lgwf
      agents/
      scripts/
      resources/
    02_confirm_business_flow/
      workflow.lgwf
      agents/
      scripts/
      resources/
    03_confirm_step_designs/
      workflow.lgwf
      agents/
      scripts/
      resources/
    06_summarize_create_result/
      workflow.lgwf
      scripts/
```

`wf/` 是唯一 workflow package root，真实入口固定为 `wf/workflow.lgwf`。根目录不得再生成可运行的 `workflow.lgwf`。

workflow 拓扑只允许两层：

- 第一层：`wf/workflow.lgwf`，只通过 `STEP ... WORKFLOW "NN_stage/workflow.lgwf"` 编排业务阶段。
- 第二层：`wf/<stage>/workflow.lgwf`，承载该阶段内部的 `PY`、`CODEX`、`REACT`、`APPROVAL`、`ROUTE` 等具体逻辑。

子 workflow 目录必须自包含 prompt 和阶段私有资源：一个 `wf/<stage>/` 目录应包含该阶段需要的 `workflow.lgwf`、`agents/`、`scripts/`、`resources/` 或阶段私有文档。禁止再创建 `wf/<stage>/<substage>/workflow.lgwf` 这类孙级 workflow；如果阶段内部有多个节点、确认点、ReAct 循环或脚本，应全部放在同一个 `wf/<stage>/workflow.lgwf` 中编排。

共享 Python helper 可放入 `wf/shared/scripts/` 并被阶段脚本通过 Python import 复用。`PROMPT`、`PROMPT_REF`、`SPEC` 引用必须留在对应 `wf/<stage>/` 目录内；不得把阶段 prompt 放入共享目录。

`ws/` 与 `wf/` 同级，只作为 LGWF work-dir。运行态只能写入 `ws/.lgwf`，不得向目标 package 根目录写入 `.lgwf`。

## package_profile

`package_profile` 决定根目录是否暴露为 Codex skill。

| profile | 用途 | 根 `SKILL.md` |
| --- | --- | --- |
| `internal_workflow_package` | 可迁移到 `lgwf-wf-tools/workflows/*` 的内部 workflow package | 不生成 |
| `skill_wrapped_workflow` | 包了 `wf/` workflow 的 Codex skill package | 生成 |

默认 profile 是 `internal_workflow_package`。

当 `package_profile=skill_wrapped_workflow` 时，根 `SKILL.md` 只能作为 skill 入口说明和路由封装，不能承载内部 workflow 的详细运行逻辑。内部 workflow 规则仍写在根 `AGENTS.md` 和 `wf/**/resources` 中。

## 路径规则

- 所有 `target_package_root` 和 resource path 必须使用包内相对路径。
- 禁止绝对路径、盘符路径、URL、`..` 和指向 `.lgwf` 的路径。
- 生成文件必须落在目标 package 内。
- `docs/steps/*.md` 是步骤设计草案目录，文件名使用 kebab-case。
- `wf/**/workflow.lgwf`、`agents/*.md`、`scripts/*.py` 和 `resources/` 必须保持相对引用。
- `workflow.lgwf` 只能出现在 `wf/workflow.lgwf` 与 `wf/<stage>/workflow.lgwf` 两类位置。

## scaffold_plan 契约

`scaffold_package` 必须根据已确认的 `.lgwf/create_requirements.json`、`.lgwf/business_flow.json` 和 `scaffold_package_template.json` 生成确定性 `scaffold_plan`。

`scaffold_plan` 至少包含：

- `workflow_name`
- `target_package_root`
- `package_profile`
- `template.template_id`
- `template.template_version`
- `rules.path_policy`
- `rules.state_boundary`
- `create_dirs`
- `create_files`
- `placeholders`
- `derived_from_business_flow`

后续 `design_steps_react` 和 `implement_steps_react` 必须优先遵循 `scaffold_plan`，不得自行发明与模板冲突的根目录结构。

## 阶段职责

`scaffold_package` 保持确定性 Python 节点，不改成 ReAct。它只负责把已确认输入和模板转换成脚手架计划，不负责自由设计、语义补全或生成最终文件内容。

`define_requirements` 聚合原始意图整理、需求 proposal 和需求确认。

`design_structure` 聚合业务流 proposal、业务流确认和 scaffold plan。

`implement_draft` 聚合步骤设计 proposal、步骤设计确认和初稿实现。

`design_steps_react` 负责把 `scaffold_plan` 和业务流转拆成 `docs/steps/*.md` 设计草案。步骤设计必须说明每个步骤如何遵循本规范。

`implement_steps_react` 负责按已确认步骤设计落地初稿。实现阶段必须遵循 `package_profile`、`wf/` 唯一 workflow root 和 `ws/.lgwf` 状态边界。

## 禁止事项

- 不得在目标 package 根目录生成 `workflow.lgwf`。
- 不得生成孙级 workflow，例如 `wf/<stage>/<substage>/workflow.lgwf`。
- 不得把阶段私有 prompt 或资源放到全局目录来绕过子 workflow 自包含边界。
- 允许把跨阶段 Python helper 放入 `wf/shared/scripts/`；共享 helper 不得包含阶段 prompt、approval prompt 或 workflow DSL。
- `internal_workflow_package` 不得生成根 `SKILL.md`。
- 不得把 `.lgwf`、`.tmp`、`__pycache__` 写入源码树。
- 不得把 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 或 E2E 运行保证混入当前 scaffold 阶段。
