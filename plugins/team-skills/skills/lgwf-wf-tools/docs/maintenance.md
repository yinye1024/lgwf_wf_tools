# Facade 维护说明

本文保存 `lgwf-wf-tools` 的显式命令、bundled client 更新和最小验证说明。

## 显式命令

- `/lgwf-wf-tools`：执行入口预检；如果 doctor 通过，继续理解用户目标；如果 doctor 失败且存在 `assets/lgwf-client-assist.zip`，自动运行 init 后再次 doctor；如果仍失败，停止并报告。
- `/lgwf-wf-tools help` 或 `/lgwf-wf-tools 帮助`：只展示帮助，不修改文件，不派发内部 workflow，不启动 LGWF run，不运行会写 `.local/` 的 self-improve 命令；帮助内容必须包含“可用指令”。
- `/lgwf-wf-tools init`：运行 `python scripts/init_lgwf_wf_tools.py`，同步临时 zip 到 vendor，安装 vendor 内 bundled LGWF wheel，输出初始化报告；不派发内部 workflow。
- `/lgwf-wf-tools doctor`：只运行 `python scripts/doctor_lgwf_wf_tools.py`，输出只读健康检查报告；不修改文件，不派发内部 workflow。需要完整审计时运行 `python scripts/doctor_lgwf_wf_tools.py --deep`。
- `/lgwf-wf-tools list`：只运行 `python scripts/list_workflows.py`，只读列出 `registry.json` 中可派发的内部 workflow；不派发内部 workflow。
- `/lgwf-wf-tools self-improve`、`/lgwf-wf-tools 自我优化`、用户说“复盘这个 facade”“优化交互体验”“把这次问题沉淀成 case”：进入 self-improve 路由。

`commands.json` 是对外指令的机器可读清单。维护显式命令时必须同步更新 `commands.json`，并运行：

```powershell
python scripts/complete_commands.py "<prefix>"
```

例如：

```powershell
python scripts/complete_commands.py "/lgwf-wf-tools d"
```

## 更新 Bundled Client

1. 将新的 `lgwf-client-assist.zip` 临时复制到 `assets/lgwf-client-assist.zip`。
2. 执行 `python scripts/init_lgwf_wf_tools.py`。
3. 确认 `vendor/lgwf-client-assist/.lgwf-client-assist-vendor.json` 记录了新的 `zip_sha256`，且 `assets/lgwf-client-assist.zip` 已被删除。
4. 确认 `.local/init/last-init.json` 中 `install.passed=true`，并记录了 bundled wheel 的 `wheel_sha256`、`bundled_version` 和 `installed_version`。
5. 提交 `vendor/lgwf-client-assist/` 的实际内容变更；不要提交 zip 包。

## 最小验证

```powershell
Get-ChildItem -LiteralPath plugins\team-skills\skills\lgwf-wf-tools -Recurse -Filter SKILL.md
```

该命令应只返回根目录 `SKILL.md`。
