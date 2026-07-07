# Skill Packaging Workflow 指引

## 模块类型

- `tool_workflow`
- registry id：`skill-packaging`
- 脚本入口：`scripts/package_lgwf_skill.py`

本目录遵循 `workflows/01-share/module-contract.md` 的 `tool_workflow` 契约，用于把已有 LGWF workflow Codex skill 打包为自包含 skill。它不是独立 Codex skill，也不作为 LGWF runtime workflow 从 registry 启动；根目录不生成 `SKILL.md`。

## 模块定位

本 workflow 负责通过脚本完成“读取源 skill、复制 runtime、生成打包清单、验证输出”的打包流程。`wf/` 下的 LGWF 初稿仅作为历史设计材料，不是 registry 当前入口。

## 入口

- registry entry：`registry.json` 中的 `skill-packaging`
- 执行入口：`scripts/package_lgwf_skill.py`
- 入口契约：`entry_contract.json`
- 主要参数：`--source-skill`、`--output-parent`、可选 `--runtime-source` 和 `--force`

## 依赖

- 依赖 `workflows/01-share/module-contract.md` 的 `tool_workflow` 模块契约。
- 依赖 facade vendor 中的 `lgwf-client-assist` runtime 作为默认打包源。
- 依赖源 skill 自身包含 `SKILL.md`、`AGENTS.md`、`README.md` 和 `wf/workflow.lgwf`。

## 状态边界

- 运行期不维护 LGWF `work_dir`。
- 只允许写入 `entry_contract.json` 声明的 `output_parent/source_skill_name` 目录。
- 只有显式传入 `--force` 时才允许覆盖已有输出目录。

## 产物

- 打包后的 Codex skill 目录。
- `PACKAGING_MANIFEST.json`。
- 脚本 JSON 输出摘要。

## 最小验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\skill-packaging\tests -p test_scaffold_package_rules.py
python skills\lgwf-wf-tools\workflows\skill-packaging\scripts\package_lgwf_skill.py --help
```

## 禁止事项

- 不要把本目录注册为 `lgwf_workflow_package`。
- 不要通过 `lgwf.py run` 启动 `wf/` 下历史初稿。
- 不要把运行状态写入源码树根目录。
- 不要在未传 `--force` 时覆盖已有打包产物。
- 不要修改 facade `vendor/` 内容；只复制到打包输出目录。
