# 步骤设计确认

请确认当前实现范围是否只覆盖已批准步骤：

- `approve`：进入确定性落盘与校验
- `reject`：当前 workflow 终止

检查重点：

- 已批准 `wf/docs/steps/*.md` 已复制到 package 内
- 根 workflow 只编排四个第一层阶段
- 关键实现动作落在脚本，不由 Agent 直接落盘
