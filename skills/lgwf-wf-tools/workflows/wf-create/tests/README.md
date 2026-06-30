# tests

这里放 `lgwf-wf-create` 的最小结构性验证入口。

## 当前覆盖范围

- `python -m unittest discover tests` 作为最小验证入口，集中检查 `wf/` workflow 结构性 audit、关键文件存在性、相对路径规则、`ws/.lgwf` 工作目录边界和中文 UTF-8 文档基线。
- `lgwf_wf_create_real_positive_e2e.py` 是真实 Codex 正向 E2E 的手动入口，文件名不以 `test_` 开头，因此不会进入 `unittest discover` 默认测试集。
- 关键文件与目录存在性。
- workflow resource path 只使用相对路径。
- `scaffold_package` 的路径规则：只使用相对路径，禁止绝对路径与 `..`。
- `scaffold_package` 的状态边界：脚手架只创建目标 package 框架，不向目标 package 根目录写入 `.lgwf`，运行状态仍归 `ws/.lgwf`。
- 步骤设计阶段的文档模板、确认决策结构和实现阶段边界约定。
- `summarize_create_result` 的运行时结果汇总接口和报告路径。

## 建议验证命令

在 `skills/lgwf-wf-tools/workflows/wf-create` 目录执行：

```powershell
python -m unittest discover tests
```

如需手动运行真实 Codex 正向 E2E，可单独执行：

```powershell
python tests\lgwf_wf_create_real_positive_e2e.py
```

预期结果：

- 验证入口会检查根目录没有 `workflow.lgwf` 和 `SKILL.md`，真实入口固定为 `wf/workflow.lgwf`。
- 验证入口会检查 `wf/workflow.lgwf` 的阶段顺序、approval route 与 resource path，仅允许包内相对路径。
- 验证入口会检查 `README.md`、`AGENTS.md`、`tests/README.md` 和 `summarize_create_result` 脚本能够以 UTF-8 正常读取，且中文说明可读。
- 验证入口会检查 `wf/09_summarize_create_result/scripts/summarize_create_result.py` 已定义第一版结果汇总接口，不暗示后续 workflow 已集成。
- 如需单独验证脚手架规则函数，可额外执行 `python -m unittest tests.test_scaffold_package_rules`。

未覆盖范围：

- 当前 run 不执行真实目标 package 创建。
- 当前 run 只有在对应 approval 为 `approve` 时才固化 `.lgwf/create_requirements.json`、`.lgwf/business_flow.json` 或 `.lgwf/step_designs.json`。
- 当前 run 不向目标 package 根目录写入 `.lgwf`。
- 当前 run 不验证 `lgwf-wf-prompt-fix` 自动调用、生成出的目标 workflow 自动接入 facade 路由、自动修复或端到端业务成功。
