# LGWF E2E Test Generator 指引

本目录是 `lgwf-wf-tools` facade 下的内部 workflow package，职责是为一个已有 LGWF workflow 生成端到端测试骨架和验收入口。它不是独立 Codex skill，不得单独注册；外部只能通过 `lgwf-wf-tools` 根目录 `SKILL.md` 和 `registry.json` 派发到本目录的 `workflow.lgwf`。

## 业务职责

- 读取用户指定的目标 `workflow.lgwf`，分析目标 workflow package 的 DSL、prompt、script、上下文文件和节点拓扑。
- 把目标 workflow 的测试需求拆成固定三层：脚本级分支覆盖、runtime + fake Codex 编排覆盖、真实 Codex 正向业务闭环验收。
- 在目标 workflow 的测试目录中生成或刷新对应测试文件，并在本次运行的 work dir 中保留设计、生成、观察和最终报告产物。
- 统一 fake Codex 的契约，避免测试依赖 Codex 调用顺序、Windows 命令行长参数或真实模型不稳定输出。

本 workflow 只负责生成测试，不负责修复目标 workflow 本身。如果扫描或生成过程中发现目标 workflow DSL、prompt 或 runtime 行为不满足测试生成前提，应在报告中说明，并由 facade 路由到 `wf-fix`、`wf-prompt-fix` 或 `wf-prompt-upgrade`。

## 适用场景

- 已有 workflow package 准备交付，需要补齐可回归的 E2E 测试。
- 已有 workflow 需要把脚本逻辑、LGWF runtime 编排和真实 Codex 验收分层验证。
- 需要为包含 `CODEX`、`REACT`、approval 或多 step 编排的 workflow 建立 fake Codex 正向路径。
- 需要生成一个真实 Codex 正向测试文件，供人工在发布前显式执行。

不适合的场景：

- 目标目录还没有可解析的 `workflow.lgwf`。
- 用户当前目标是修复失败 workflow，而不是生成测试；应优先使用 `wf-fix`。
- 用户只想改 prompt 质量或上下游契约；应优先使用 `wf-prompt-fix` 或 `wf-prompt-upgrade`。

## 输入契约

入口 `collect_target_request` approval 接收 JSON object：

```json
{
  "workflow_lgwf": "D:/path/to/target-workflow/workflow.lgwf",
  "workflow_root": "D:/path/to/target-workflow",
  "test_output_dir": "tests",
  "test_name_prefix": "target_workflow"
}
```

- `workflow_lgwf` 必填，可以是用户机器上的绝对路径。
- `workflow_root` 可省略，默认使用 `workflow_lgwf` 所在目录。
- `test_output_dir` 可省略，默认由 workflow 推导；通常是目标 workflow package 下的 `tests`。
- `test_name_prefix` 可省略，默认由目标 workflow 名称推导。
- workflow package 内部引用 `SCRIPT`、`PROMPT`、`CONTEXT workflow` 时仍必须使用相对路径，不允许绝对路径或 `..`。

## 业务流程

1. `prepare_target_request_context`：准备 approval 所需上下文，提示用户提交目标 workflow 信息。
2. `collect_target_request`：人工确认目标 workflow、输出目录和测试命名前缀。
3. `inspect_target`：校验输入，扫描目标 package，解析 workflow graph，并总结业务流。
4. `derive_coverage_matrix`：根据目标 graph 和资源文件生成覆盖矩阵，明确每类测试要覆盖的节点、分支、输入输出和断言。
5. `script_flow_e2e`：通过 `REACT` 循环设计、生成、校验脚本级 E2E 测试；不启动目标 LGWF runtime。
6. `runtime_fake_e2e`：通过 `REACT` 循环设计、生成、校验 runtime fake E2E 测试；启动真实 LGWF runtime，但 Codex runner 使用 Python fake。
7. `real_positive_e2e`：通过 `REACT` 循环设计、生成、校验真实 Codex 正向测试；该测试作为人工验收入口，默认不进入自动回归集合。
8. `finish`：生成最终报告，汇总生成文件、覆盖范围、验证结果和后续风险。

三个生成阶段都采用 `REACT MAX 3`：先设计测试，再落地文件，最后观察校验结果；如果观察不通过，由对应 `decide_*` 脚本决定是否继续修复循环。

## 固定输出

目标 workflow 的测试目录中固定生成三类文件，文件名以前缀推导：

```text
test_<workflow>_script_flow_e2e.py
test_<workflow>_runtime_fake_e2e.py
test_<workflow>_real_positive_e2e.py
```

运行 work dir 中会保留中间产物和报告：

```text
.lgwf/e2e_target_request.json
.lgwf/e2e_target_request.normalized.json
.lgwf/e2e_workflow_sources.json
.lgwf/e2e_workflow_graph.json
.lgwf/e2e_business_flow_summary.json
.lgwf/e2e_coverage_matrix.json
.lgwf/e2e_*_design.json
.lgwf/e2e_*_generation.json
.lgwf/e2e_*_observe.json
reports/e2e-test-generator/report.json
reports/e2e-test-generator/report.md
```

## 测试生成约束

- 固定生成三类测试，不提供裁剪开关；如用户只想要其中一类，应先说明该 workflow 当前不支持局部生成。
- `script_flow_e2e` 关注目标 scripts、内置 tool 调用、输入输出文件和分支断言，不应启动目标 workflow runtime。
- `runtime_fake_e2e` 必须使用 Python fake Codex，prompt 必须通过 `--prompt-file` 传递，避免长 prompt 走命令行参数。
- `runtime_fake_e2e` 应验证 LGWF runtime 编排、state/result 文件、approval 或 fake response 契约，不依赖真实 Codex。
- `real_positive_e2e` 必须保持人工显式执行语义，默认不纳入 `unittest discover` 回归集合。
- 生成测试时优先复用目标 workflow 已有测试工具、fixture 和命名风格；没有现成模式时再创建最小必要 helper。
- 生成内容必须保持 UTF-8；中文说明、JSON 示例和报告不允许写成本地 ANSI/GBK。

## 使用方式

本 workflow 应由 `lgwf-wf-tools` facade 派发：

1. 读取 facade 根目录 `registry.json` 中 `e2e-test-generator` 的 `workflow_lgwf`、`work_dir` 和 `agents_md`。
2. 读取本文件，按输入契约准备 `--input-json`；涉及中文或复杂 JSON 时优先写入 UTF-8 文件再传递。
3. 使用 bundled client 启动并持续跟进同一个 run：

```powershell
$lgwfPy = "skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy run --workflow-lgwf skills\lgwf-wf-tools\workflows\e2e-test-generator\workflow.lgwf --work-dir <registry-work-dir> --input-json <json> --background
python $lgwfPy status --session-id <session-id>
python $lgwfPy wait --session-id <session-id>
```

进入 `waiting_human` 时，只能提交用户明确确认的目标 workflow 信息或验收选择。不要绕过 approval，也不要在未确认旧 work dir 状态时直接启动第二个 run。

## 本 package 自检

修改本 workflow package 后，至少执行：

```powershell
$lgwfPy = "skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py"
python $lgwfPy audit skills\lgwf-wf-tools\workflows\e2e-test-generator\workflow.lgwf
python -m unittest discover skills\lgwf-wf-tools\workflows\e2e-test-generator\tests
```

如果只修改本说明文件，可以不运行完整 workflow，但应确认 UTF-8 内容可读、路径示例仍与当前目录结构一致。
