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
    02_confirm_requirements/
      00_collect_raw_intent/
      01_propose_requirements_react/
    04_confirm_business_flow/
      03_propose_business_flow_react/
      05_scaffold_package/
    07_confirm_step_designs/
      06_design_steps_react/
      08_implement_steps_react/
    09_summarize_create_result/
```

`wf/` 是唯一 workflow package root，真实入口固定为 `wf/workflow.lgwf`。根目录不得再生成可运行的 `workflow.lgwf`。

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
- `internal_workflow_package` 不得生成根 `SKILL.md`。
- 不得把 `.lgwf`、`.tmp`、`__pycache__` 写入源码树。
- 不得把 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 或 E2E 运行保证混入当前 scaffold 阶段。
