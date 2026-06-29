---
name: lgwf-wf-runner
description: Use when Codex needs to launch, inspect, or continue an LGWF workflow run with an isolated per-run workspace, especially for concurrent runs of workflows registered by lgwf-wf-tools. Handles session-scoped work_dir resolution, launch session manifests, status lookup, and session listing; does not route business goals, submit approvals, lock target packages, or modify workflow source files.
---

# LGWF Workflow Runner

本 skill 负责为 LGWF workflow 提供隔离运行目录。它只解决 run workspace 隔离问题，不负责业务路由、目标 package 锁、approval 决策或 workflow 修复。

## 使用边界

- 使用同级 `lgwf-wf-tools/registry.json` 读取 workflow 定义。
- 只把 registry 中的 `work_dir` 当作 legacy 信息和 workflow 元数据，不作为新 run 的写入目录。
- 每次启动前生成独立目录：`lgwf-wf-runner/ws/sessions/<workflow_id>/<facade_session_id>/`。
- 后续 `status`、`approval`、`runs` 必须使用 manifest 中记录的 `resolved_work_dir`。
- 不判断多个 run 是否修改同一个目标 package；用户和上层 facade 负责避免目标文件冲突。

## 快速流程

1. 解析隔离工作目录：

```powershell
python plugins/team-skills/skills/lgwf-wf-runner/scripts/resolve_work_dir.py --workflow-id wf-create --target-slug lgwf-wf-thinking --create
```

2. 启动 workflow：

```powershell
python plugins/team-skills/skills/lgwf-wf-runner/scripts/launch_workflow.py --workflow-id wf-create --target-slug lgwf-wf-thinking --input-json '{"raw_intent":"..."}'
```

3. 查询 session 状态：

```powershell
python plugins/team-skills/skills/lgwf-wf-runner/scripts/status_session.py --facade-session-id <id>
```

4. 列出已知 sessions：

```powershell
python plugins/team-skills/skills/lgwf-wf-runner/scripts/list_sessions.py
```

## 脚本说明

- `scripts/resolve_work_dir.py`：读取 registry，生成或校验 session-scoped `work_dir`。
- `scripts/launch_workflow.py`：调用 `lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py run --background`，并写入 session manifest。
- `scripts/status_session.py`：按 manifest 查找真实 `work_dir`，再调用 `lgwf.py status`。
- `scripts/list_sessions.py`：扫描 `*/ws/sessions/*/.lgwf/main_agent/facade_session.json` 并汇总。

## 输出约定

所有脚本默认输出 UTF-8 JSON。上层 agent 不应把完整 JSON 原样贴给用户；应摘要展示 session id、workflow id、resolved work dir、当前状态和下一步操作。

## 禁止事项

- 不要直接删除已有 session 目录。
- 不要用 `lgwf-wf-tools` registry 里的 `work_dir` 查询一个 runner session。
- 不要自动 approve 或 reject human approval。
- 不要把 target package lock 逻辑塞进本 skill。
