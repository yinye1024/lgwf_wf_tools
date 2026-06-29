# LGWF Codex Plugins

这个仓库维护 LGWF 相关的 Codex plugin。当前主要 plugin 是 `team-skills`，用于分发 `lgwf-wf-tools` workflow facade。

## 目录结构

- `.agents/plugins/marketplace.json`：团队 marketplace manifest。
- `plugins/team-skills/`：Codex plugin 根目录。
- `plugins/team-skills/.codex-plugin/plugin.json`：plugin manifest，声明 plugin 名称、版本、展示信息和 skills 入口。
- `plugins/team-skills/skills/lgwf-wf-tools/`：当前对外发布的 LGWF workflow facade skill。

## 本地安装

在仓库根目录执行：

```powershell
codex plugin marketplace add D:\allen\github\lgwf_plugins
codex plugin add team-skills@lgwf-team
```

安装或更新后，重新打开一个 Codex thread，让新 skill 列表重新加载。

## 发布到团队

把本仓库推送到 Git 仓库后，团队成员可以用 Git marketplace 安装：

```powershell
codex plugin marketplace add https://github.com/<org>/<repo> --ref main
codex plugin add team-skills@lgwf-team
```

更新已安装 marketplace：

```powershell
codex plugin marketplace upgrade
```

## 维护 Skill

新增 skill 放在 `plugins/team-skills/skills/<skill-name>/`。目录名使用小写 hyphen-case，每个 skill 必须包含 `SKILL.md`，并让 `SKILL.md` 聚焦 Codex 需要遵循的操作流程。

如果这个 plugin 继续只发布 LGWF facade，应保持 `skills/` 下只有 `lgwf-wf-tools` 和必要的临时开发资料；临时资料不要在 `SKILL.md` 中声明为对外入口。

发布前至少运行：

```powershell
$env:PYTHONUTF8="1"
python C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py plugins\team-skills\skills\lgwf-wf-tools
python -m json.tool plugins\team-skills\.codex-plugin\plugin.json > $null
python -m json.tool .agents\plugins\marketplace.json > $null
```
