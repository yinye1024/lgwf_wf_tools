# LGWF Workflow 使用说明

## 自动安装并运行

优先使用随包 runner script。它会从 `assets/` 强制安装随包 wheel，覆盖本机旧 `lgwf`，然后运行 workflow：

本文中的 `<skill-dir>` 指源码、打包或安装后的 `lgwf-client-assist` facade 根目录。Agent 统一使用 `scripts/lgwf.py`。

`<work_dir>` 不能等于 workflow package。推荐放在 package 外部；如果位于 package 内部，runner 会在复制 snapshot 时排除整个 work dir。`data/`、`reports/` 和 `.lgwf/` 等运行内容只写入 work dir。

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-json <workflow_json> --work-dir <work_dir> --input-json "{}"
```

`.lgwf` 是优先维护的 authoring source；`workflow.json` 仍是 runtime IR。运行 authoring source时，wrapper 会把 package 复制到 `<work_dir>/.lgwf/workflow/`，在隐藏 snapshot 中 audit、compile 和运行，用户 package 不生成 `workflow.json`：

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json "{}"
```

复制按文件字节执行，不转换文本编码或换行。`.git/`、`__pycache__/`、`.lgwf-compiled-*` 和 package 内部的整个 work dir 不进入 snapshot；symlink、junction 或其他 reparse point 会使启动失败。snapshot 会保留到下一次 rerun，由现有 work-dir 清理流程删除。

安装策略由打包时生成的 `assets/package-profile.json` 决定：

- `dev` 是默认 profile。每次执行实际 facade 命令前都会比较随包 wheel 的 SHA-256 与上次安装记录；hash 不一致或记录缺失时强制重装，hash 一致时跳过，适合版本号未变化的本地迭代。
- `prd` 仅在未安装 `lgwf`，或已安装版本与随包 wheel 版本不一致时安装。
- `run --force-install` 在任意 profile 下都强制重装。
- `doctor` 始终只读，不触发安装。
- 缺少 manifest 时按 `dev` 处理；非法 manifest 会明确报错。

打包命令：

```powershell
.\scripts\package_lgwf.ps1
.\scripts\package_lgwf.ps1 -Profile prd
```

## 旧运行数据处理

如果 `<work_dir>\.lgwf` 已包含上次 workflow 的运行数据，runner 会先在终端提示选择：

- 输入 `rerun`：清空 `<work_dir>` 下的旧内容并重新运行 workflow，保留 `<work_dir>` 目录本身。
- 输入 `continue`：不启动新 workflow，输出现有 workflow 的 status / pending human requests / latest run 信息。

rerun 清理前由 `scripts/lgwf_env_init/work_dir_guard.py` 检查 `work_dir`：

- 空目录可以继续运行。
- 非空目录必须包含可识别的 hidden workflow snapshot、LGWF run、process、human approval、main-agent session、runtime log 或有效 `.lgwf/context.json` artifact。
- 识别失败时返回 `not an LGWF work directory`，不停止进程、不安装 wheel、不删除任何文件。

执行 rerun 清理前，`scripts/lgwf_env_init/work_dir_guard.py` 会判断非空 `work_dir` 是否为 LGWF 工作目录。目标必须包含 `.lgwf`，且至少存在 `workflow/workflow.lgwf`、`workflow/workflow.json`、`runs/`、`processes/`、`human/`、`main_agent/`、`codex/`、`logs/` 或 `context.json` 之一；否则返回退出码 2，保留全部文件。

自动化场景可以跳过交互：

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-json <workflow_json> --work-dir <work_dir> --input-json "{}" --rerun-existing
python <skill-dir>\scripts\lgwf.py run --workflow-json <workflow_json> --work-dir <work_dir> --input-json "{}" --continue-existing
python <skill-dir>\scripts\lgwf.py run --workflow-json <workflow_json> --work-dir <work_dir> --input-json "{}" --resume-existing
```

`--continue-existing` 只报告已有进程、pending human request 和 latest run 状态，不从失败节点恢复执行。

`--resume-existing` 会查找 `.lgwf/checkpoints/<run_id>/checkpoint.json` 中最新的 failed checkpoint，并从失败节点重新执行；已完成前序节点不会重跑，失败节点本身会重跑一次。指定 `--resume-run-id <run_id>` 可恢复某个 run；调试新版 workflow 时可追加 `--resume-allow-workflow-changed` 跳过 workflow hash 一致性检查。

后台模式发现旧 `.lgwf` 数据且未提供上述 flag 时，不会等待 stdin；runner 会返回退出码 `2`，并在 stdout 输出 `requires_existing_workflow_decision=true` 的 JSON。主 agent 必须在 chat 中询问用户选择，然后用 `--rerun-existing`、`--continue-existing` 或 `--resume-existing` 重新执行同一命令。

长 workflow 需要可见 Windows 控制台时，加 `--show-console`：

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json "{}" --show-console
```

runner 会输出 workflow process id，打开 `cmd` 窗口运行 `lgwf_client.cli`，并在结束后保留窗口。`--show-console` 不能和 `--output-json` 同时使用。

客户端窗口会在 stderr 输出 workflow 进度，包括 node start、wait、completion、failure 和 output summary。

facade 内部仍委托原有 runner、DSL 和 client CLI。兼容入口见 `references/compatibility-cli.md`。

`audit` 是 authoring 阶段入口，只检查 workflow package，不读取运行状态：

```powershell
python <skill-dir>\scripts\lgwf.py audit <workflow_lgwf>
```

Windows shortcut：

```powershell
<skill-dir>\assets\run_lgwf_workflow.bat --workflow-json <workflow_json> --work-dir <work_dir> --input-json "{}"
```

## Doctor

只检查环境和输入路径，不安装、不编译、不运行：

```powershell
python <skill-dir>\scripts\lgwf.py doctor
python <skill-dir>\scripts\lgwf.py doctor --workflow-json <workflow_json> --work-dir <work_dir>
python <skill-dir>\scripts\lgwf.py doctor --workflow-lgwf <workflow_lgwf> --work-dir <work_dir>
```

Doctor 会报告当前 Python、bundled wheel、已安装 `lgwf` 版本、`lgwf_client` / `lgwf_dsl` import 状态，以及可选路径状态。

## Smoke Test

解包 skill 后运行随包 smoke workflow：

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-json <skill-dir>\assets\examples\shell_smoke\workflow.json --work-dir <work_dir> --input-json "{}"
```

## 保存 Final State

使用 `--output-json` 把 final-state JSON 写入文件：

```powershell
python <skill-dir>\scripts\lgwf.py run --workflow-json <workflow_json> --work-dir <work_dir> --input-json "{}" --output-json <state.json>
```

`--output-json` 是最终 runtime state。启用 `--record true` 时，`<work_dir>\.lgwf\runs\` 包含 run audit records。

## Client Tools

```powershell
python <skill-dir>\scripts\lgwf.py tool list
python <skill-dir>\scripts\lgwf.py tool describe copy_file
python <skill-dir>\scripts\lgwf.py tool run copy_file --options-json '{"source":"a.bin","destination":"b.bin"}'
```

公开 tools 为 `ensure_dir`、`write_text_file`、`file_replace`、`copy_file`、`copy_directory`。前三者要求 `--work-dir`；复制 CLI 可使用绝对路径或基于当前目录的相对路径。workflow `TOOL` 和兼容 builtin 中的路径始终限制在 workspace 内。

## Minimal Workflow

```json
{
  "nodes": [
    {
      "id": "run_shell",
      "capability": "exec.run_shell",
      "config": {
        "command": "echo hello"
      }
    }
  ],
  "edges": [],
  "routes": [],
  "entry_point": "run_shell"
}
```

## Builtin Script Example

新建 `.lgwf` 时，稳定 client 工具使用原生 `TOOL`：

```lgwf
TOOL ensure_output
  USE ensure_dir
  OPTIONS {"path": "out"}
  RESULT state.ensure_output_result;
```

`TOOL` 的 options 会在 audit 和 runtime 中按 tool catalog 校验，workflow 路径始终限制在 `work_dir`。旧 `exec.run_python builtin_script` JSON 保持兼容。

```json
{
  "id": "ensure_output",
  "capability": "exec.run_python",
  "config": {
    "builtin_script": "ensure_dir",
    "options": {
      "path": "out"
    }
  }
}
```

## Check Example

```json
{
  "id": "check_output",
  "capability": "flow.check",
  "config": {
    "check": "file_exists",
    "options": {
      "path": "out/result.json"
    }
  }
}
```
