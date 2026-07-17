# LGWF Workflow Runner 指引

## 模块类型

- `codex_skill`
- 脚本型 runner，不包含 `workflow.lgwf`

## 模块定位

本 skill 只负责 LGWF workflow 的隔离启动和 session 查询。它不替代 `lgwf-wf-tools` 的业务路由、approval 边界、监控规则或 self-improve 流程。

## 入口

- `scripts/resolve_work_dir.py`
- `scripts/launch_workflow.py`
- `scripts/status_session.py`
- `scripts/list_sessions.py`

## 依赖

- 默认读取同级 `lgwf-wf-tools/registry.json`。
- 启动 workflow 时调用 `lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py`。

## 状态边界

- registry 中的 `work_dir` 只作为 legacy 信息和 workflow 元数据，不是 runner 的写入目录。
- 本次 run 的最终目录必须是：`lgwf-wf-runner/ws/sessions/<workflow_id>/<facade_session_id>/`。
- 启动后必须保存 `facade_session.json`，后续 status、approval 和 run artifacts 都以该 manifest 的 `resolved_work_dir` 为准。

## 产物

- `ws/sessions/<workflow_id>/<facade_session_id>/.lgwf/main_agent/facade_session.json`
- 底层 LGWF run 写出的 `.lgwf/` 运行记录。

## 核心规则

- 不做 target package 锁；如果两个 run 修改同一个目标目录，风险由上层调用者或用户承担。

## 最小验证

```powershell
python C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\lgwf-wf-runner
python skills\lgwf-wf-runner\scripts\resolve_work_dir.py --workflow-id wf-create-fast --target-slug smoke --create
python skills\lgwf-wf-runner\scripts\list_sessions.py
```

## 禁止事项

- 不要把 registry 中的 legacy `work_dir` 当作 runner session 的写入目录。
- 不要自动 approve 或 reject approval。
- 不要把目标 package lock 逻辑塞进本 skill。
