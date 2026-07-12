# tests

这里放 `lgwf-wf-create` 的最小结构性验证入口。

## 当前覆盖范围

- `python -m unittest discover tests` 作为最小验证入口，集中检查 `wf/` workflow 结构性 audit、关键文件存在性、相对路径规则、`ws/.lgwf` 工作目录边界和中文 UTF-8 文档基线。
- `lgwf_wf_create_real_positive_e2e.py` 是真实 Codex 正向 E2E 的手动入口，文件名不以 `test_` 开头，因此不会进入 `unittest discover` 默认测试集。
  该入口会先对原始 `wf/workflow.lgwf` 执行 `lgwf.py audit`，再在隔离临时 workspace 中启动真实 `lgwf.py run --auto-human`；如果 unresolved approval、超时或失败，会保留 `fixtures/`、`artifacts/`、`work/.lgwf/` 和已生成目标包，供后续 `wf-fix` 或人工诊断。
- `lgwf_wf_create_real_positive_e2e_for_wf_fix.py` 是 `wf-fix` 正向 E2E 的手动入口，文件名不以 `test_` 开头，因此不会进入 `unittest discover` 默认测试集。
  该入口复用普通真实正向 fixture，先对原始 `wf/workflow.lgwf` 执行 `lgwf.py audit`，再以 `skills/lgwf-wf-tools/workflows/wf-fix/wf/workflow.lgwf` 启动 `wf-fix`；即使 pre-run audit 提前失败，也会先保留 `wf_fix_run.stdout.txt`、`wf_fix_run.stderr.txt` 和 `wf_fix_failure_summary.json` 占位，再连同 `wf-fix` work dir、`target_runs/attempt-*`、fixture 和最后一轮 target run 的目标包一起留给后续诊断。
- `test_lgwf_wf_create_runtime_package_e2e.py` 是确定性运行时 E2E：使用真实 LGWF runtime、临时 workspace 和 fake Codex，完整跑通 wf-create 从需求确认到实现、audit、汇总、handoff 的主链路。
- 关键文件与目录存在性。
- workflow resource path 只使用相对路径。
- `scaffold_package` 的路径规则：只使用相对路径，禁止绝对路径与 `..`。
- `scaffold_package` 的状态边界：脚手架只创建目标 package 框架，不向目标 package 根目录写入 `.lgwf`，运行状态仍归 `ws/.lgwf`。
- REVIEW 确认节点固定使用 `approve`、`revise`、`reject` 三选项：`approve` 固化 confirmed artifact，`revise` 带完整 JSON 重入同一 REVIEW 节点，`reject` 通过 `FAIL_ALL` 终止。
- 步骤设计阶段的文档模板、REVIEW 决策结构和实现阶段边界约定。
- `summarize_create_result` 的运行时结果汇总接口和报告路径。

## 建议验证命令

在 `skills/lgwf-wf-tools/workflows/wf-create` 目录执行：

```powershell
python -m unittest discover tests
```

如需单独运行确定性运行时 E2E，可执行：

```powershell
python -m unittest tests.test_lgwf_wf_create_runtime_package_e2e
```

如需手动运行真实 Codex 正向 E2E，可单独执行：

```powershell
python tests\lgwf_wf_create_real_positive_e2e.py
```

该入口会自动写入最小 `raw_intent` fixture，固定验证生成 `skills/runtime-e2e-created` 两阶段 package；成功时清理临时 workspace，失败时保留完整工作区。

如需手动运行 `wf-fix` 正向 E2E，可单独执行：

```powershell
python tests\lgwf_wf_create_real_positive_e2e_for_wf_fix.py
```

该入口会自动提交 `target_workflow_lgwf`、`target_workflow_input`、`max_attempts=5` 和 `ask_main_agent_for_target_approvals=true`，并在最后一轮 target run 上复验 `create_result_summary.json`、`create_result_report.md`、authoring audit 和 `python -m unittest discover tests`；如果失败，会在 `artifacts/wf_fix_failure_summary.json` 中汇总失败阶段、关键输入和保留路径。

预期结果：

- 验证入口会检查根目录没有 `workflow.lgwf` 和 `SKILL.md`，真实入口固定为 `wf/workflow.lgwf`。
- 验证入口会检查 `wf/workflow.lgwf` 的阶段顺序、REVIEW route 与 resource path，仅允许包内相对路径。
- 验证入口会检查 `README.md`、`AGENTS.md`、`tests/README.md` 和 `summarize_create_result` 脚本能够以 UTF-8 正常读取，且中文说明可读。
- 验证入口会检查 `wf/06_summarize_create_result/scripts/summarize_create_result.py` 已定义第一版结果汇总接口，不暗示后续 workflow 已集成。
- 如需单独验证脚手架规则函数，可额外执行 `python -m unittest tests.test_scaffold_package_rules`。
- 确定性运行时 E2E 会创建临时 package，校验生成出的 `workflow.lgwf`、阶段子 workflow、`implementation_audit_result.json`、`implementation_observe.json`、`implementation_result.json`、`create_result_summary.json` 和 `post_fix_handoff_input.json`，并确认 fake Codex 至少覆盖需求、业务流、步骤设计、实现和 observe audit 阶段。
- 调试确定性运行时 E2E 时，可以设置 `LGWF_WF_CREATE_RUNTIME_E2E_KEEP_WORKDIR=1` 保留临时目录。

未覆盖范围：

- 当前 run 只有在对应 REVIEW decision 为 `approve` 时才固化 `.lgwf/create_requirements.json`、`.lgwf/business_flow.json` 或 `.lgwf/step_designs.json`。
- 当前 run 不向目标 package 根目录写入 `.lgwf`。
- 当前 run 不验证 `lgwf-wf-prompt-fix` 自动调用、生成出的目标 workflow 自动接入 facade 路由、自动修复或端到端业务成功。
