# repo-context-pack 协作指引

## 模块定位

模块类型：`codex_skill`，并内嵌一个 LGWF workflow package。

`repo-context-pack` 是一个带内嵌 LGWF workflow 的 Codex skill，用于为目标仓库或模块生成 AI agent 可接手的上下文包。第一版聚焦只读扫描、结构化报告和交接摘要，不修改目标源码。

## 入口

- Codex skill 入口：`SKILL.md`。
- 脚本入口：`scripts/build_context_pack.py`。
- LGWF workflow 入口：`wf/workflow.lgwf`。
- 运行目录：`ws/`，运行状态只允许写入 `ws/.lgwf/`。

## 依赖

- Python 标准库。
- 仓库内的 `skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py` 用于 audit 或按 workflow 运行。
- 不依赖 facade registry；本 skill 第一版不自动注册为内部 workflow。

## 状态边界

- `target_dir` 默认只读。
- 上下文包只写入 `output_dir`。
- 禁止在目标 package 根目录写入 `.lgwf`、`.tmp`、`__pycache__` 或运行态缓存。
- 所有 workflow resource path 必须是包内相对路径，禁止绝对路径、盘符路径和 `..`。

## 产物

- `repo_context_pack.md`：主上下文报告。
- `agent_handoff.md`：交接摘要。
- `module_map.json`：模块地图。
- `command_inventory.json`：命令清单。
- `risk_register.md`：风险和边界。
- `read_order.md`：推荐阅读顺序。
- `summary.json`：扫描统计和产物索引。

## 验证

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\repo-context-pack\wf\workflow.lgwf
python -m unittest discover skills\repo-context-pack\tests
python -m compileall -q skills\repo-context-pack
```

## 禁止事项

- 不得修改 `target_dir` 内源码文件。
- 不得执行 Git 写操作、发布、registry 注册或自动审批。
- 不得把 `vendor`、`.git`、`.lgwf`、`ws`、`.venv`、`node_modules` 等目录复制进上下文包。
- 不得生成根目录 `workflow.lgwf`；唯一 workflow root 是 `wf/workflow.lgwf`。
