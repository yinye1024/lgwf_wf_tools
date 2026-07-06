# Facade 维护说明

本文保存 `lgwf-wf-tools` 的帮助、初始化、诊断、列表、bundled client 更新、发布保护和最小验证说明。本仓库已经改为纯 skills 包，不再维护 plugin command Markdown。

## 显式命令

- `/lgwf-wf-tools`：执行入口预检；如果 doctor 通过，继续理解用户目标；如果 doctor 失败且存在 `assets/lgwf-client-assist.zip`，自动运行 init 后再次 doctor；如果仍失败，停止并报告。
- `/lgwf-wf-tools help` 或 `/lgwf-wf-tools 帮助`：只展示帮助，不修改文件，不派发内部 workflow，不启动 LGWF run，不运行会写 `.local/` 的 self-improve 命令；帮助内容必须包含“可用指令”。
- `/lgwf-wf-tools init`：运行 `python scripts/init_lgwf_wf_tools.py`，同步临时 zip 到 vendor，安装 vendor 内 bundled LGWF wheel，同时检查 Codex 是否已通过 link 方式安装 `lgwf-wf-tools` 并指向当前 skill 根目录；未安装、普通目录安装或 link 指向错误时会自动调整，输出初始化报告；不派发内部 workflow。
- `/lgwf-wf-tools doctor`：只运行 `python scripts/doctor_lgwf_wf_tools.py`，输出只读健康检查报告；不修改文件，不派发内部 workflow。需要完整审计时运行 `python scripts/doctor_lgwf_wf_tools.py --deep`。
- `/lgwf-wf-tools list`：只运行 `python scripts/list_workflows.py`，只读列出 `registry.json` 中可派发的内部 workflow；不派发内部 workflow。

目标 workflow 直启命令见 [target-run.md](target-run.md)。给目标 workflow 播种自包含 self-improve 结构见 [self-improve-seed.md](self-improve-seed.md)。self-improve 场景见 [self-improve.md](self-improve.md)。
把带 `wf/workflow.lgwf` 的 Codex skill 打包成自包含 skill 时，路由到 `skill-packaging`，并读取 `workflows/skill-packaging/AGENTS.md`。

## 脚本级代理入口

- `scripts/run_skill_workflow.py`：供 `git-diff-brief`、`lgwf-wf-thinking` 等外部 skill 调用。该脚本不解析业务参数，只把收到的参数原样透传给本 facade 内置的 `vendor/lgwf-client-assist/scripts/lgwf.py run`，用于避免外部 skill 依赖 bundled `lgwf.py` 的具体路径。
- 调用方必须显式传入 `lgwf.py run` 所需参数，例如 `--workflow-lgwf`、`--work-dir`、`--input-json-file`、`--background`、`--rerun-existing`、`--continue-existing` 或 `--resume-existing`。
- PowerShell 中不要把 JSON 直接塞进 `--input-json`。第一次启动也应先写 UTF-8 no BOM 临时 input JSON 文件，再传 `--input-json-file`；这样可以避免双引号、中文、换行或嵌套 JSON 被 shell 转义破坏。只有纯 ASCII 的空对象 `--input-json "{}"` 可作为临时 smoke 用法。

示例：

```powershell
$inputPath = "D:/tmp/lgwf-input.json"
[System.IO.File]::WriteAllText($inputPath, "{}", [System.Text.UTF8Encoding]::new($false))
python skills\lgwf-wf-tools\scripts\run_skill_workflow.py --workflow-lgwf skills\git-diff-brief\wf\workflow.lgwf --work-dir skills\git-diff-brief\ws --input-json-file $inputPath --background
```

维护显式命令时，更新本文件、根 `SKILL.md` 以及相关测试，并运行：

```powershell
python scripts/complete_commands.py "<prefix>"
```

例如：

```powershell
python scripts/complete_commands.py "/lgwf-wf-tools d"
```

## 更新 Bundled Client

1. 将新的 `lgwf-client-assist.zip` 临时复制到 `skills\lgwf-wf-tools\assets\lgwf-client-assist.zip`。
2. 执行 `python scripts/init_lgwf_wf_tools.py`。
3. 确认 `vendor/lgwf-client-assist/.lgwf-client-assist-vendor.json` 记录了新的 `zip_sha256`，且 `skills\lgwf-wf-tools\assets\lgwf-client-assist.zip` 已被删除。
4. 确认 `.local/init/last-init.json` 中 `install.passed=true`，并记录了 bundled wheel 的 `wheel_sha256`、`bundled_version` 和 `installed_version`。
5. 确认 `.local/init/last-init.json` 中 `codex_skill.passed=true`，且 `codex_skill.after.target` 指向当前 `skills\lgwf-wf-tools` 目录。
6. 提交 `vendor/lgwf-client-assist/` 的实际内容变更；不要提交 zip 包。

## 发布保护

发布包不得覆盖或删除 `.local/self-improve/`、`.local/overrides/` 或 `.local/upgrade-reports/`。这些目录保存运行期历史、私有 override 和本地升级报告，不属于发布包基线。

## 最小验证

修改 `SKILL.md`、`AGENTS.md`、`registry.json`、`workflows/*/AGENTS.md`、`workflows/**/workflow.lgwf`、`scripts/init_lgwf_wf_tools.py`、`scripts/doctor_lgwf_wf_tools.py`、`scripts/validate_registry.py`、`scripts/list_workflows.py` 或 vendor manifest 后，运行：

```powershell
python workflows/self-improve/scripts/run_self_evals.py
```

只检查 facade 自包含时运行：

```powershell
python scripts/doctor_lgwf_wf_tools.py
```

```powershell
Get-ChildItem -LiteralPath skills\lgwf-wf-tools -Recurse -Filter SKILL.md
```

该命令应只返回根目录 `SKILL.md`。
