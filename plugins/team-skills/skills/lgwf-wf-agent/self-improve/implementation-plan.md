# lgwf-wf-agent 自我提升机制实现方案

## Summary

为 `lgwf-wf-agent` 增加一套“证据驱动、可发布、可保留本地历史”的 self-improve 机制。它不自动修改自身；它通过 skill 对话、变更脚本/CI、发布前检查、真实失败复盘四类触发，产出 incident、eval case、review report、proposal 和 scorecard。发布包覆盖时只覆盖基线模板，不覆盖本地积累和团队私有 override。

参考实践：生产级 agent 需要固定 eval set、整体行为链路评测、运行可观测性和发布前回归闸门，而不是只依赖单次成功运行。

## Key Changes

- `self-improve/` 保存发布包内基线内容：说明文档、闭环文档、eval schema、baseline cases、templates、scorecard 指标和只读脚本。
- `.local/` 保存运行期和本地私有内容：incidents、reports、proposals、scorecards、overrides 和 upgrade reports。
- `AGENTS.md` 说明 self-improve 的触发、产出、发布保护和 override 边界。
- `scripts/run_self_evals.py` 做确定性回归检查，不调用 LLM judge，不修改发布文件。
- `scripts/record_incident.py` 只在用户确认后记录真实问题。
- `scripts/create_proposal.py` 从 incident 或 eval report 生成可审查 proposal，不自动 apply。

## Trigger Model

- Skill 触发：用户要求复盘、沉淀 case、生成 proposal 或运行 self eval。
- 变更触发：修改 facade、registry、内部 workflow 指引、workflow source 或 vendor manifest 后运行 self eval。
- 失败触发：路由、approval、监控、旧 work dir 或报告问题出现后，经用户确认记录 incident。
- 发布触发：发布前运行 self eval；升级后保留 `.local/` 并写 upgrade report。

## Release / Preservation Rules

- 发布包可以覆盖 `SKILL.md`、`AGENTS.md`、`registry.json`、`workflows/`、`vendor/`、`scripts/` 和 `self-improve/` 基线。
- 发布包不得覆盖或删除 `.local/self-improve/`、`.local/overrides/` 或 `.local/upgrade-reports/`。
- 本地 override 只能补充或收紧规则，不能绕过 approval、vendor client、路径安全、UTF-8、单 skill facade 或固定 workflow 路由约束。
- 第一版不自动合并 override；冲突只报告风险并等待人工处理。

## Test Plan

- 静态结构：检查 self-improve 文件、根 `SKILL.md` 唯一性、registry 路径和 vendor 指引。
- Self eval：验证 routing、monitoring、approval baseline case 可通过，并输出 JSON/Markdown report。
- Incident/proposal：验证 UTF-8 incident 和 proposal 生成。
- 发布保护：确认 `.local/` 被忽略并作为运行期状态目录保留。

## Assumptions

- 第一版只做文档、schema、确定性 eval 和本地产物目录。
- 第一版不新增自动自我修改 workflow。
- `.local/` 作为本地状态目录；如未来插件发布机制不保留 skill 内 `.local/`，再迁移到用户级目录。
- `vendor/lgwf-client-assist` 仍是主 agent loop、approval 和 run artifacts 查询的权威来源。
