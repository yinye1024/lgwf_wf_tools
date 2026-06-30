# LGWF Codex Skills

这个仓库维护 LGWF workflow tools 的 Codex skills。每个目录都是可单独安装、复制或验证的 skill，不再使用额外发布层。

## 目录结构

- `skills/git-diff-brief/`：生成 Git 变更中文摘要的 workflow skill。
- `skills/lgwf-wf-runner/`：管理 LGWF workflow 运行工作目录和会话的辅助 skill。
- `skills/lgwf-wf-thinking/`：把 workflow 创建、修复、转换和治理诉求整理成可确认方案的 skill。
- `skills/lgwf-wf-tools/`：LGWF workflow facade skill，负责路由、监控、审批和自我优化。
- `tests/`：仓库级回归测试。

## 本地安装

按需把单个 skill 目录复制到本机 Codex skills 目录。例如：

```powershell
$target = "$env:USERPROFILE\.codex\skills\lgwf-wf-tools"
Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item -LiteralPath D:\allen\github\lgwf_skills\skills\lgwf-wf-tools -Destination $target -Recurse
```

安装或更新后，重新打开一个 Codex thread，让 skill 列表重新加载。

## 分发方式

把本仓库推送到 Git 仓库后，团队成员直接按需复制 `skills/<skill-name>/`。仓库只维护 skill 源码和验证资产。

## 维护 Skill

新增 skill 放在 `skills/<skill-name>/`。目录名使用小写 hyphen-case，每个 skill 必须包含 `SKILL.md`，并让 `SKILL.md` 聚焦 Codex 需要遵循的操作流程。

开发草稿、复现说明、临时 preset 和运行报告不要放进 `skills/`，除非它们属于某个正式 skill 的文档或测试夹具。

修改单个 skill 后至少运行：

```powershell
$env:PYTHONUTF8="1"
python C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\lgwf-wf-tools
```
