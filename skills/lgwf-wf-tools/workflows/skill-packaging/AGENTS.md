# Skill Packaging 指引

## 模块类型

- `tool_workflow`
- registry id：`skill-packaging`

## 模块定位

本 tool workflow 负责把已有 LGWF workflow Codex skill 打包成自包含 skill。产物内置 `vendor/lgwf-client-assist`，通过产物自己的 `scripts/run_local_lgwf_workflow.py` 启动 `wf/workflow.lgwf`，不依赖 `lgwf-wf-tools` facade、registry 或外部 skill。

## 入口

- registry entry：`scripts/package_lgwf_skill.py`
- 路由入口：根 `SKILL.md` 的 `/lgwf-wf-tools package-skill <path>`、`/lgwf-wf-tools pack-skill <path>`，以及 `AGENTS.md` 中“打包自包含 skill”的用户场景。

示例：

```powershell
python skills\lgwf-wf-tools\scripts\package_lgwf_skill.py --source-skill skills\wf-audit-fix --output-parent .local\packager-smoke --force
```

## 依赖

- 源 skill 必须包含 `SKILL.md`、`AGENTS.md`、`README.md` 和 `wf/workflow.lgwf`。
- 默认 runtime 来源为 facade 内置 `vendor/lgwf-client-assist`。
- 不读取 `lgwf-wf-tools/registry.json` 作为目标 skill 的运行依赖；registry 只负责发现本 tool workflow。

## 状态边界

- 本 tool workflow 不维护 LGWF run 状态。
- 打包输出写入调用者指定的 `--output-parent/<source-skill-name>`。
- 源 skill 的 `ws/`、`.lgwf/`、`.local/`、`reports/` 和缓存文件不进入产物。
- 产物后续运行状态写入产物自己的 `ws/`。

## 产物

- `<output-parent>/<source-skill-name>/vendor/lgwf-client-assist/`
- `<output-parent>/<source-skill-name>/scripts/run_local_lgwf_workflow.py`
- `<output-parent>/<source-skill-name>/PACKAGING_MANIFEST.json`

## 最小验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\tests -p test_package_lgwf_skill.py
python skills\lgwf-wf-tools\scripts\package_lgwf_skill.py --source-skill skills\wf-audit-fix --output-parent .local\packager-smoke --force
python .local\packager-smoke\wf-audit-fix\vendor\lgwf-client-assist\scripts\lgwf.py audit .local\packager-smoke\wf-audit-fix\wf\workflow.lgwf
```

## 禁止事项

- 不要把本 tool workflow 注册为独立 Codex skill。
- 不要复制 `lgwf-wf-tools` facade、registry 或内部 workflow 到目标产物。
- 不要复制源 skill 的运行态、历史报告或本地草稿。
- 不要自动覆盖输出目录；只有显式传入 `--force` 才允许覆盖。
- 不要自动安装、发布、压缩或提交产物。
