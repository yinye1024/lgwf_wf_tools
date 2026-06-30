# Facade 派发与监控流程

本文保存 `lgwf-wf-tools` 的初始化、派发、监控和收尾细节。入口硬规则见根目录 `AGENTS.md`。

## Facade 初始化

初始化分三层处理，不放在内部 workflow node 里：

1. Doctor 预检层：处理任何 `/lgwf-wf-tools` facade 请求前，先运行 `python scripts/doctor_lgwf_wf_tools.py`。该脚本只读检查根 `SKILL.md`、`registry.json`、registry 路径、vendor `AGENTS.md`、`scripts/lgwf.py`、bundled wheel，以及 vendor 内不得存在 `SKILL.md`。
2. Init 同步层：doctor 失败且存在 `assets/lgwf-client-assist.zip` 时，自动运行 `python scripts/init_lgwf_wf_tools.py`。它负责从临时 zip 刷新 `vendor/lgwf-client-assist/`、删除内部 `SKILL.md`、清理旧 install-state、写入 `.lgwf-client-assist-vendor.json`，删除 zip，然后安装 vendor 内 bundled LGWF wheel，并把初始化报告写入 `.local/init/last-init.json`。init 后必须再次运行 doctor。
3. 派发前预检层：doctor 通过后，准备派发内部 workflow 前再读取 `registry.json` 和目标 workflow `AGENTS.md`；缺失时直接报告 facade 安装不完整，不 fallback 到外部 skill。
4. Runtime 安装层：`init` 会主动安装 bundled LGWF wheel；后续 `vendor/lgwf-client-assist/scripts/lgwf.py` 在 `run`、`audit`、`status`、`approval`、`runs` 等命令需要 runtime/client 模块时仍会按 bundled wheel hash 自动校验，必要时重新安装。`doctor` 只诊断，不安装。

不要新增“初始化 workflow”来安装 wheel。内部 workflow 启动本身就依赖 `lgwf.py run` 和 bundled wheel；把安装放进 workflow node 会让安装发生得太晚。

## 派发流程

### 目标 Workflow 直启

如果用户请求显式匹配 `/lgwf-wf-tools run <path>`、`/lgwf-wf-tools target-run <path>` 或 `/lgwf-wf-tools --target-workflow <path>`，先走目标 workflow 直启，不进入 `registry.json` 候选路由。其他自然语言任务请求即使包含路径，也继续走内部 workflow 路由。

1. 解析 `<path>`：文件路径必须指向 `workflow.lgwf`；目录路径依次查找 `<path>/workflow.lgwf` 和 `<path>/wf/workflow.lgwf`。
2. 推导 `work_dir`：`<package>/wf/workflow.lgwf` 使用 `<package>/ws`，`<dir>/workflow.lgwf` 使用 `<dir>/ws`。
3. 如果无法解析出目标 workflow，直接报告失败原因，不回退到内部 workflow 路由。
4. 如果 `work_dir/.lgwf` 已存在，先询问用户选择 `continue`、`resume` 或 `rerun`。
5. 使用 bundled client 启动或继续，第一版默认使用空输入 `{}`：

```powershell
$lgwfPy = "vendor/lgwf-client-assist/scripts/lgwf.py"
python $lgwfPy run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json "{}"
```

直启后仍保存同一个 `session_id` / `pid` / `work_dir`，按下方监控循环处理 `status`、`wait`、`approval` 和收尾。

### 内部 Workflow 路由

1. 以本目录为 facade root，读取 `registry.json`，按目标 workflow id 获取 `workflow_lgwf`、`work_dir` 和 `agents_md`。
2. 路由前必须先列出可用 workflow，优先运行 `python scripts/list_workflows.py`；如果因上下文已读取 `registry.json`，也必须展示同等清单。
3. 说明为什么选择目标 workflow，再读取目标 `AGENTS.md`，确认适用场景、输入契约、approval 语义、固定输出和自检要求。
4. 根据目标 workflow 的输入契约准备 `--input-json`。涉及中文或复杂 JSON 时，优先写入 UTF-8 文件，再由脚本读取或用安全 argv 传递。
5. 使用 bundled client 启动或继续：

```powershell
$lgwfPy = "vendor/lgwf-client-assist/scripts/lgwf.py"
python $lgwfPy run --workflow-lgwf <workflow_lgwf> --work-dir <work_dir> --input-json <json> --background
python $lgwfPy status --work-dir <work_dir> --session-id <session-id>
python $lgwfPy wait
```

6. 保存同一个 `session_id` / `pid` / `work_dir`，使用 `status`、`wait`、`approval` 和 `runs` 持续推进；不要把后台启动当一次性命令。
7. 进入 `waiting_human` 时展示 workflow 给出的摘要、选项和风险，只提交用户明确确认的结果。
8. 结束后汇总最终状态、关键产物、变更文件、阻塞项和建议下一步。

## 监控循环

派发任何内部 workflow 前必须读取：

- `vendor/lgwf-client-assist/AGENTS.md`
- `vendor/lgwf-client-assist/references/agent-host-assist/guide.md`
- `vendor/lgwf-client-assist/references/agent-host-assist/cli-agent-loop.md`
- `vendor/lgwf-client-assist/references/workflow-usage.md`

本 facade 只补充这些本地约束：

- 使用本目录内置的 `vendor/lgwf-client-assist/scripts/lgwf.py`，不要 fallback 到用户 `.codex` 中的外部 skill。
- 以 `registry.json` 中的 `work_dir` 作为当前内部 workflow 的固定工作目录；如果已有旧数据，按 vendor 指引让用户选择 `continue` / `resume` / `rerun`。
- 后台启动后保存同一个 `session_id` / `pid` / `work_dir`，后续所有 `status`、`wait`、`approval` 和 `runs` 操作都围绕同一个 handle。
- `waiting_human` 不是完成状态。若是 `flow.human_approval`，按 vendor main-agent ask flow 在当前对话确认并提交；若是 `AGENT_LOOP` 控制状态但没有 human request，汇报 loop reason、evidence 和 artifact 路径，等待用户决定。
- 完成后按 vendor run artifact 查询流程读取 summary 和 changed files，再结合目标 workflow 的 `AGENTS.md` 汇总结果、变更文件、阻塞项和下一步路由建议。
