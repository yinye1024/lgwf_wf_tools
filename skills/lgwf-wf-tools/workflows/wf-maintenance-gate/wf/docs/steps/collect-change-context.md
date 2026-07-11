# collect-change-context

## step_slug

`collect-change-context`

## step_name

收集变更上下文

## goal

设计 `wf/01_collect_change_context/workflow.lgwf`，把维护 gate 的原始请求、git 变更收集、registry workflow 列表读取和仓库路径识别统一落成 `.lgwf/change_context.json`。这个阶段是后续全部分类、计划和汇总的唯一输入基线，必须保证同一轮 run 的变更来源、作用域和路径判定稳定可追踪。

## inputs

- 上游阶段或节点：
  - `maintenance_gate_request`
  - `.lgwf/business_flow.json` 中 `01_collect_change_context` 阶段定义
- 依赖文件或状态：
  - `docs_tmp/wf-maintenance-gate-development.md`
  - `.lgwf/create_reference_context/scaffold/scaffold_template_spec.md`
  - `.lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md`
- 关键约束：
  - `changed_files` 为空时才允许调用 git 收集
  - 需要同时记录收集来源：显式输入或 git 自动发现
  - 只做只读收集，不修改 `.local/`、源码树或 target package
  - 运行状态只允许写入 `ws/.lgwf`

## outputs

- 预期生成的文件：
  - `wf/01_collect_change_context/workflow.lgwf`
  - `wf/01_collect_change_context/scripts/*.py`
  - `wf/01_collect_change_context/resources/*`
  - `.lgwf/change_context.json`
- 预期生成的目录：
  - `wf/01_collect_change_context/agents/`
  - `wf/01_collect_change_context/scripts/`
  - `wf/01_collect_change_context/resources/`
- 交付给下游的结构片段：
  - 已归一化的 `maintenance_gate_request`
  - `changed_files`、来源标记、未跟踪文件、重命名/移动信息
  - 仓库根目录、facade 根目录、脚本目录、目标 workflow 根目录和 registry 路径

## dependencies

- 前置步骤：
  - `define-package-contracts`
  - `define-shared-helper-and-tests`
- 依赖节点：
  - 入口 `maintenance_gate_request`
  - `skills/lgwf-wf-tools/registry.json`
- 需要人工确认的位置：
  - 当前阶段不引入人工确认；若输入请求缺少必要字段，应输出结构化失败或明确默认值，不通过 REVIEW 补问

## implementation_suggestions

- 阶段内部优先使用确定性 Python 脚本读取输入 JSON、调用 `git status --short` 和 `git diff --name-only`，再把结果统一写入 `change_context.json`。
- 需要显式处理未跟踪文件、重命名和跨目录移动，避免后续 impact classification 漏掉 `vendor`、`shared_contract` 或 `packaging` 级别影响。
- 把仓库根、facade 根和目标 workflow 目录解析结果一并写入 artifact，后续阶段不得再次通过 `..` 或固定层级猜测路径。
- 资源目录可放最小 schema、字段说明和错误文案模板，但不要在本阶段引入验证计划、失败路由或报告模板。

## acceptance_notes

- 重点确认 `changed_files=[]` 时的 git 自动采集策略是否稳定且可复现，尤其是未跟踪文件和重命名记录。
- 重点确认本阶段不会读取 `.local/` 历史来决定当前影响面，只使用本轮请求和当前 git 事实。
- 重点确认输出中的路径都是 workspace 内可追踪路径或相对逻辑标识，不把绝对本机路径暴露为后续业务数据通道。

## out_of_scope

- `lgwf-wf-prompt-fix`
- `lgwf-wf-tools`
- 自动修复、自动重试或端到端运行保证
- 在本阶段执行 doctor、workflow tests、pre-release 或 package smoke
