# LGWF Codex Skills

这个仓库维护面向 Codex 的 LGWF workflow 工具资产。日常使用通常从 `skills/lgwf-wf-tools/` 开始：它提供统一入口，负责 workflow 路由、运行、审批、诊断、创建、修复、转换、测试生成和自我优化等流程。

根 README 只作为仓库入口页使用。具体 workflow 的输入契约、运行产物和维护细节，请继续阅读 `skills/lgwf-wf-tools/` 下的文档和各 workflow 自带说明。

## 定位

`lgwf-wf-tools` 是基于 DSL 的工作流引擎入口。LGWF runtime 通过 DSL 暴露可调用能力，主 agent 通过 DSL 编排 workflow 来实现用户意图，并在执行过程中监控 workflow 状态、失败、产物和人工确认点。

DSL 是 runtime 和主 agent 之间的协作协议：它把用户意图、runtime 能力、agent 行动、验证结果和确认边界放进同一张可追踪的 workflow graph，让 agent 和工作流的配合更丝滑。

## 模块标准

本仓库把 skill 和 workflow 都作为模块维护。模块分为三类：

- `codex_skill`：`skills/<skill>/` 下的 Codex skill package。
- `lgwf_workflow_package`：通过 `workflow.lgwf` 由 LGWF runtime 执行的 workflow package。
- `tool_workflow`：由脚本或文档入口驱动、不走 LGWF runtime 的内部 workflow。

每个模块必须能从自己的 `README.md`、`AGENTS.md` 或 registry entry 理解模块定位、入口、依赖、状态边界、产物、验证和禁止事项。详细规则见 `skills/lgwf-wf-tools/workflows/01-share/module-contract.md`。

## 什么时候使用

当你需要在 Codex 中处理 LGWF workflow 相关任务时，优先从 `lgwf-wf-tools` 开始：

- 初始化、诊断或列出可用 workflow。
- 运行已有 LGWF workflow。
- 通过主 agent 编排创建、修复或转换 LGWF workflow。
- 为 workflow 生成端到端测试。
- 对 workflow 执行 prompt 修复、prompt 升级、执行监控和后续验收。
- 做 self-improve、沉淀 case、生成 proposal 或发布前检查。

## 快速安装

把 `skills/lgwf-wf-tools/` 安装成 Codex skill。安装或更新后，重新打开一个 Codex thread，让 skill 列表重新加载。

在新 thread 中执行：

```text
/lgwf-wf-tools init
```

初始化完成后，就可以通过 `/lgwf-wf-tools` 使用内置 workflow 路由、诊断、运行和维护能力。

## 标准工作流

一个典型使用流程如下：

1. 安装 `lgwf-wf-tools` 为 Codex skill，并重新打开 Codex thread。
2. 执行 `/lgwf-wf-tools init`，完成本机初始化。
3. 用自然语言说明目标，例如“创建一个用于处理发布检查的 LGWF workflow”或“修复这个目标 workflow 的运行失败”。
4. 主 agent 通过 `lgwf-wf-tools` 选择合适的 DSL workflow，组织上下文，并在需要时要求你确认目标、范围或执行方案。
5. 你确认后，runtime 按 DSL graph 执行 workflow，主 agent 持续监控状态、失败、产物和等待点。
6. 执行完成后，查看交付结果、验证建议和后续动作；如果结果需要调整，继续在同一个 thread 中提出修订。

## 常用入口

在 Codex 中可以直接使用这些入口表达意图：

```text
/lgwf-wf-tools help
/lgwf-wf-tools init
/lgwf-wf-tools doctor
/lgwf-wf-tools list
/lgwf-wf-tools run <path>
/lgwf-wf-tools self-improve
```

也可以用自然语言描述任务，例如“帮我修复这个 LGWF workflow”或“给这个 workflow 生成 E2E 测试”。`lgwf-wf-tools` 会根据当前请求路由到合适的内部 workflow。

## 任务导航

| 我想做什么 | 推荐入口 |
| --- | --- |
| 初始化本机 `lgwf-wf-tools` 环境 | `/lgwf-wf-tools init` |
| 查看帮助、诊断环境、列出 workflow | `/lgwf-wf-tools help`、`/lgwf-wf-tools doctor`、`/lgwf-wf-tools list` |
| 运行已有 LGWF workflow | `/lgwf-wf-tools run <path>` |
| 创建新的 LGWF workflow | 通过 `/lgwf-wf-tools` 路由到 `wf-create` |
| 修复目标 workflow | 通过 `/lgwf-wf-tools` 路由到 `wf-fix` |
| 转换已有 prompt workflow | 通过 `/lgwf-wf-tools` 路由到 `wf-convert` |
| 生成 E2E 测试 | 通过 `/lgwf-wf-tools` 路由到 `e2e-test-generator` |
| 做 prompt 修复、升级和后续验收 | 通过 `/lgwf-wf-tools` 路由到 `wf-post-fix` |
| 做自我优化、沉淀 case、生成 proposal | `/lgwf-wf-tools self-improve` |

## 标准两层结构

LGWF workflow package 推荐使用两层结构：外层 package 负责说明、测试和工作目录，内层 `wf/` 才是真正的 workflow root。

```text
my-workflow-package/
  README.md
  AGENTS.md
  wf/
    workflow.lgwf
    artifact_contracts.json
    01_prepare_target/
      workflow.lgwf
      agents/
      resources/
    02_run_and_review/
      workflow.lgwf
      agents/
      resources/
    shared/
  ws/
```

关键约束：

- `wf/` 是唯一 workflow root，真实入口固定为 `wf/workflow.lgwf`。
- 外层 package 根目录不放可运行的 `workflow.lgwf`。
- 第一层 `wf/workflow.lgwf` 只负责编排业务阶段，保持薄编排。
- 第二层 `wf/<stage>/workflow.lgwf` 承载该阶段内部节点、确认点、路由和私有资源。
- 不创建 `wf/<stage>/<substage>/workflow.lgwf` 这类孙级 workflow。
- `ws/` 与 `wf/` 同级，只作为运行工作目录；运行状态落在 `ws/.lgwf`。

## DSL 说明

根 `workflow.lgwf` 通常只描述阶段顺序，并通过相对路径引用第一层子 workflow：

```lgwf
WORKFLOW example_package;
ENTRY prepare_target;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 900;
}

STEP prepare_target
  WORKFLOW "01_prepare_target/workflow.lgwf";

STEP run_and_review
  WORKFLOW "02_run_and_review/workflow.lgwf";

FLOW prepare_target
  THEN run_and_review;
```

阶段内的 `workflow.lgwf` 再描述具体工作节点。下面是一个概念片段，用于说明常见节点关系：

```lgwf
WORKFLOW prepare_target;
ENTRY collect_target;

APPROVAL collect_target
  PROMPT_REF "confirm_target.md"
  RESULT state.example.target;

CODEX inspect_target
  PROMPT "agents/inspect_target.md"
  INPUT state.example.target
  OUTPUT_JSON ".lgwf/target_report.json" AS_FILE
  RESULT state.example.target_report;

FLOW collect_target
  THEN inspect_target;
```

DSL 里的路径应保持包内相对路径。prompt、确认模板和阶段私有资源优先放在对应 `wf/<stage>/` 目录内；跨阶段共享材料再放入 `wf/shared/`。

## 目录结构

- `skills/lgwf-wf-tools/SKILL.md`：Codex skill 入口，负责第一跳路由和使用边界说明。
- `skills/lgwf-wf-tools/AGENTS.md`：workflow router 的协作指令。
- `skills/lgwf-wf-tools/registry.json`：可路由 workflow 注册表。
- `skills/lgwf-wf-tools/docs/`：维护命令、输入契约、目标运行和自我优化说明。
- `skills/lgwf-wf-tools/workflows/`：内置 LGWF workflow package 和 tool workflow。
- `skills/lgwf-wf-tools/vendor/lgwf-client-assist/`：随 skill 分发的 LGWF 运行辅助客户端。
- `tests/`：仓库级回归测试。

## 维护与验证

根 README 不展开底层维护命令。维护者修改 `lgwf-wf-tools` 或内部 workflow 时，优先阅读对应目录下的 `README.md`、`AGENTS.md`、`docs/` 和 `tests/`，再按变更范围选择验证方式。

用户侧只需要确认 `lgwf-wf-tools` 已安装为 Codex skill，并在新 thread 中执行 `/lgwf-wf-tools init`。
