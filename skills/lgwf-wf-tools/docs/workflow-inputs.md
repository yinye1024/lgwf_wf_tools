# 各 Workflow 输入摘要

本文只保存 facade 准备 `--input-json` 时的常用摘要。机器可读事实源是 `registry.json` 指向的各 workflow `entry_contract.json`；目标 workflow `AGENTS.md` 负责解释业务纪律和人工确认边界。

## PowerShell 输入建议

在 PowerShell 中不要把 JSON 直接塞进 vendor `lgwf.py run --input-json`，否则双引号容易被 shell 处理掉，中文和换行也可能在命令参数层损坏。内部 workflow 优先用 `scripts/run_skill_workflow.py --workflow-id <id>` 启动；它会按 `entry_contract.json` 自动补 runtime 路径、固定 `work_dir`，并把 inline JSON 写入 UTF-8 no BOM 临时文件后改用 `--input-json-file`。

推荐方式：

```powershell
python scripts\run_skill_workflow.py --workflow-id wf-create-fast --input-json-file D:/tmp/lgwf-input.json --background
```

如果输入很短，也可以把 JSON 交给代理脚本转换：

```powershell
python scripts\run_skill_workflow.py --workflow-id wf-create-fast --input-json '{"raw_intent":"要创建的新 LGWF workflow 原始意图"}' --background
```

底层排障或直连 vendor runtime 时，仍应先把 JSON 写入 UTF-8 no BOM 文件，再使用 `--input-json-file`：

```powershell
$inputPath = "D:/tmp/lgwf-input.json"
$inputJson = @'
{
  "raw_intent": "要创建的新 LGWF workflow 原始意图"
}
'@
[System.IO.File]::WriteAllText($inputPath, $inputJson, [System.Text.UTF8Encoding]::new($false))

python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py run --workflow-lgwf <workflow.lgwf> --work-dir <ws> --input-json-file $inputPath --background
```

vendor runtime 也可以使用 `--input-json @D:/tmp/lgwf-input.json`。只有纯 ASCII 的空对象 `--input-json "{}"` 可作为临时 smoke 用法。

## `--auto-human` 策略

`scripts/run_skill_workflow.py --workflow-id <id> --auto-human` 会读取目标 `entry_contract.json`：

- `allowed` / `conditional`：显式传入时透传给 runtime。
- `forbidden`：拒绝启动并提示该 workflow 不能自动通过 human gate。
- `not_applicable`：用于 `tool-workflow`，不通过 LGWF runtime human gate。

`--auto-human` 只覆盖 LGWF runtime 的 `flow.human_approval`、`flow.human_review` 和已接入的 `flow.human_choice` 策略，不覆盖 handoff、`agent_loop waiting_human` 或 `subgraph.react on_max`。

## wf-fix

契约：`workflows/wf-fix/entry_contract.json`。

`wf-fix` 启动时使用空 JSON object：

```json
{}
```

它会在第一个 approval 中询问 `target_workflow_lgwf`、`max_attempts` 和 `ask_main_agent_for_target_approvals`，随后再收集目标 workflow 自己的业务输入。

## wf-prompt-fix

契约：`workflows/wf-prompt-fix/entry_contract.json`。

推荐输入：

```json
{
  "prompt_fix_target": {
    "target_workflow_lgwf": "D:/example/workflow.lgwf",
    "target_package_root": "D:/example",
    "target_dirs": ["D:/example"]
  }
}
```

## wf-prompt-upgrade

契约：`workflows/wf-prompt-upgrade/entry_contract.json`。

推荐输入：

```json
{
  "prompt_upgrade_target": {
    "target_workflow_lgwf": "D:/example/workflow.lgwf",
    "target_package_root": "D:/example",
    "target_dirs": ["D:/example"]
  }
}
```

## wf-create-fast

契约：`workflows/wf-create-fast/entry_contract.json`。

`wf-create-fast` 是 registry 中唯一对外可见、可启动的创建 workflow 入口。它确认需求、确认业务流、落盘 scaffold，并通过 HANDOFF 交给主 agent 继续完善。旧 `wf-create` 已删除且不在 registry 中，不作为可选择或可启动入口。

### wf-create-fast 启动前输入模板

如果用户没有明确目标、没有提供 `raw_intent`，或只说“帮我创建 workflow”，主 agent 不直接启动 `wf-create-fast`。先让用户补充一份可启动输入，至少覆盖：

- 目标：这个 workflow 要完成什么。
- 输入：用户会提供什么数据、文件或目录。
- 输出：最终要生成什么产物。
- 人工确认点：哪些地方需要用户确认、评审或选择。
- 目标目录：希望生成到哪里。
- 非目标：哪些事情不要做。

用户已有初步计划、需求说明或验收说明时，可以提供计划文档路径，例如 `D:/example/workflow-plan.md`。主 agent 读取后先整理为 `raw_intent`，把计划文档路径放入 `request.target_file`；多个参考文件放入 `request.target_files`。整理后的 JSON 必须展示给用户确认后再启动。

推荐输入：

```json
{
  "raw_intent": "要创建的新 LGWF workflow 原始意图"
}
```

带计划文档路径的推荐输入：

```json
{
  "raw_intent": "根据初步计划创建一个新的 LGWF workflow，目标、输入、输出、确认点和非目标以计划文档为准。",
  "request": {
    "target_file": "D:/example/workflow-plan.md"
  }
}
```

简单创建请求示例：

```json
{
  "raw_intent": "创建一个简单 LGWF workflow，先确认需求和业务流，生成 scaffold 后交给主 agent 完善实现。",
  "request": {
    "target_file": "D:/example/workflow-plan.md"
  }
}
```

## wf-convert

契约：`workflows/wf-convert/entry_contract.json`。

推荐输入：

```json
{
  "prompt_convert_target": {
    "target_dir": "D:/example/prompt-workflow",
    "entry_files": ["README.md"],
    "target_workflow_name": "example-workflow",
    "target_package_root": "skills/example-workflow"
  }
}
```

## e2e-test-generator

契约：`workflows/e2e-test-generator/entry_contract.json`。

`e2e-test-generator` 会通过入口 approval 收集目标信息，目标 JSON 形态为：

```json
{
  "workflow_lgwf": "D:/example/workflow.lgwf",
  "workflow_root": "D:/example",
  "test_output_dir": "tests",
  "test_name_prefix": "example_workflow"
}
```

## tool-workflow

`lgwf-guide`、`target-run`、`self-improve` 和 `self-improve-seed` 使用工具参数或普通对话，不走 LGWF `--input-json`。对应入口契约分别是：

- `workflows/lgwf-guide/entry_contract.json`
- `workflows/target-run/entry_contract.json`
- `workflows/self-improve/entry_contract.json`
- `workflows/self-improve-seed/entry_contract.json`

`skill-packaging` 是 `lgwf` workflow，使用 `packaging_request` 作为 `--input-json-file` 入口，不属于 `tool-workflow`。
