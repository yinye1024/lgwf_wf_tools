# lgwf-wf-runner

`lgwf-wf-runner` 是脚本型 Codex skill，用于为 `lgwf-wf-tools` registry 中的 LGWF workflow 创建隔离 session work dir，并提供启动、查询和列出 session 的脚本入口。

## 模块类型

- `codex_skill`
- 脚本型 runner，不包含自有 `wf/workflow.lgwf`

## 入口

```powershell
python skills/lgwf-wf-runner/scripts/resolve_work_dir.py --workflow-id wf-create --target-slug smoke --create
python skills/lgwf-wf-runner/scripts/launch_workflow.py --workflow-id wf-create --target-slug smoke --input-json-file D:/tmp/input.json
python skills/lgwf-wf-runner/scripts/status_session.py --facade-session-id <id>
python skills/lgwf-wf-runner/scripts/list_sessions.py
```

## 依赖

- 默认读取同级 `skills/lgwf-wf-tools/registry.json`。
- 启动 workflow 时调用 `skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py`。

## 状态与产物

- 每次运行写入 `skills/lgwf-wf-runner/ws/sessions/<workflow_id>/<facade_session_id>/`。
- session manifest 写入 `.lgwf/main_agent/facade_session.json`。

## 验证

```powershell
python -m unittest discover skills\lgwf-wf-runner\tests
python skills\lgwf-wf-runner\scripts\list_sessions.py
```
