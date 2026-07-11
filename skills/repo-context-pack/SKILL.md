---
name: repo-context-pack
description: 扫描指定仓库或模块目录，生成 AI agent 可快速接手的上下文包；默认只读目标源码，只写 output_dir。
---

# repo-context-pack

当用户需要为一个本地仓库、模块、Codex skill 或 LGWF workflow package 快速生成交接上下文时，使用本 skill。

## 能力边界

- 输入 `target_dir`、可选 `output_dir`、`focus`、`depth` 和 `max_files`。
- 默认只读 `target_dir`，不会修改目标源码、修复 bug、生成测试或提交 Git。
- 只向 `output_dir` 写入上下文包产物；未指定时写入 `target_dir/.local/context-packs/<目录名>`。
- 内嵌 LGWF workflow 位于 `wf/workflow.lgwf`，运行状态应写入同级 `ws/.lgwf/`。

## 主要入口

- 脚本直跑：`python scripts\build_context_pack.py --target-dir <repo> --output-dir <out> --focus onboarding --depth normal`
- LGWF audit：`python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\repo-context-pack\wf\workflow.lgwf`

## 输出产物

- `repo_context_pack.md`
- `agent_handoff.md`
- `module_map.json`
- `command_inventory.json`
- `risk_register.md`
- `read_order.md`
- `summary.json`
