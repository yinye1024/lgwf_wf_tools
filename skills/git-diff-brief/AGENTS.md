# git-diff-brief 协作指引

## 模块类型

- `codex_skill`
- 内嵌 `lgwf_workflow_package`，真实 workflow root 为 `wf/`

## 模块定位

- 当前目录是 `internal_workflow_package`，真实 workflow root 仅在 `wf/`。
- 根目录提供 `SKILL.md` 作为 Codex skill 入口，但不生成可运行的根 `workflow.lgwf`。
- 本包用于读取 Git 仓库变更上下文，生成中文 Markdown 变更摘要初稿和建议 commit message，并在人工确认后可选执行 stage/commit。

## 入口

- Codex 入口：`SKILL.md`。
- LGWF 入口：`wf/workflow.lgwf`。
- 启动本包 workflow 时，必须通过已注册的 `lgwf-wf-tools` 调用 `scripts/run_skill_workflow.py`，并显式传入 `--workflow-lgwf skills/git-diff-brief/wf/workflow.lgwf` 与 `--work-dir skills/git-diff-brief/ws`。

## 依赖

- 依赖 `lgwf-wf-tools` facade 的 workflow 启动代理。
- 依赖目标 Git 仓库的真实 diff/status/log 数据。

## 状态边界

- 所有 workflow 资源路径必须保持包内相对路径。
- 不得在源码树根目录写入 `.lgwf`、绝对路径或 `..`。
- 本包运行时默认使用同级 `ws/` 作为 work dir；运行状态只允许写入 `ws/.lgwf`。

## 产物

- 变更摘要 Markdown、commit message 建议、delivery decision 和可选 commit plan 写入 `ws/.lgwf/`。
- `self-improve/` 产物按该子模块自己的 `AGENTS.md` 写入。

## workflow 结构

- `wf/workflow.lgwf` 只编排五个第一层业务阶段子 workflow。
- `wf/<stage>/workflow.lgwf` 承载阶段内具体节点、确认点和脚本调用。
- 禁止创建 `wf/<stage>/<substage>/workflow.lgwf`。

## 当前实现范围

- 已补齐请求范围对齐、Git 上下文采集、摘要生成、结果复核与交付、Git 提交动作五个阶段的最小目录与文件。
- `self-improve/` 提供本 workflow 的自包含自我提升模块，可记录 incident、生成 proposal、跑结构 eval、执行静态 trace readiness 和生成 scorecard。
- `self-improve trace-eval` 默认只做 `audit` + `compile`，不无人值守启动完整摘要 runtime；真实 runtime trace 需通过 `lgwf-wf-tools` 正常 rerun 获取。
- 业务脚本必须读取真实输入并执行真实 Git 采集；不得用固定空数据或假结果替代业务逻辑。
- fake Codex 响应只允许存在于测试夹具中，用于验证编排连通性，不得混入运行时业务产物。
- 默认不得执行 Git 写操作；只有最终审批明确选择 `commit_action=stage` 或 `commit_action=commit` 时，才允许基于采集到的 `relative_scope` 执行 `git add` / `git commit`。
- 面向用户的交互运行不得使用 `skip_delivery_review=true`。该开关只允许无人值守摘要生成，且只能配合 `delivery_action=none` 跳过最终人工确认。
- `1`、`2`、`3`、`4`、`5` 只是在 `confirm_delivery_or_revision` REVIEW 节点等待输入时有效；workflow 已结束后不得把用户单独回复的编号解释成 `git add` 或 `git commit`。
- 当 `relative_scope` 为空字符串时表示仓库根目录；除非 REVIEW 决策显式带 `allow_repo_root_write=true`，否则 `stage` / `commit` 必须失败并保持不执行 Git 命令。
- 不包含 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成、自动修复和端到端成功保证。

## 验证

```powershell
python -m unittest discover skills\git-diff-brief\tests
```

## 禁止事项

- 不要直接调用 `vendor/lgwf-client-assist/scripts/lgwf.py run` 启动本 workflow。
- 不要在未获得最终审批时执行 `git add` 或 `git commit`。
