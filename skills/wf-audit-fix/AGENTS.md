# wf-audit-fix 模块指引

本目录是独立 Codex skill，内嵌 LGWF workflow package。Codex 入口为 `SKILL.md`，真实 LGWF 入口固定为 `wf/workflow.lgwf`，运行态只允许写入 `ws/.lgwf` 或 `ws/reports`。

## 模块定位

- 模块类型：`codex_skill`，内嵌 `lgwf_workflow_package`。
- 本 skill 不由 `lgwf-wf-tools/registry.json` 派发；启动 workflow 时通过 `lgwf-wf-tools` 的 `scripts/run_skill_workflow.py` 代理执行。
- 目标：对用户指定的旧 `workflow.lgwf` 先做真实目录 `audit`，失败后仅在隔离 candidate 副本中修复静态 DSL / audit 问题；candidate 通过后再 promote 回真实目录并复检。
- 非目标：不运行目标 workflow 业务、不收集业务 `input-json`、不处理目标 workflow 自身 approval、不自动接入 `wf-post-fix`。

## 入口

- Codex 入口：`SKILL.md`
- 运行入口：`wf/workflow.lgwf`
- 根文档：`README.md`
- 最小验证：`tests/test_scaffold_package_rules.py`

## 依赖

- 依赖 `skills/lgwf-wf-tools/scripts/run_skill_workflow.py` 启动内嵌 workflow。
- 依赖 `skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py audit`
- 依赖目标 workflow package 本身可被静态读取
- 依赖 `wf/shared/scripts/` 提供共用路径、JSON、audit 和复制辅助

## 状态边界

- 源码包内只保存 workflow、脚本、资源和测试。
- 运行态产物只写入 `ws/.lgwf` 或 `ws/reports`。
- candidate 副本位于运行态目录，不写回源码树 `.lgwf`。

## 固定产物

- `ws/.lgwf/wf_audit_fix/input.json`
- `ws/.lgwf/wf_audit_fix/runtime_context.json`
- `ws/.lgwf/wf_audit_fix/initial_audit_result.json`
- `ws/.lgwf/wf_audit_fix/initial_audit_diagnostics.json`
- `ws/.lgwf/wf_audit_fix/candidate_attempt_log.json`
- `ws/.lgwf/wf_audit_fix/post_promote_real_audit_result.json`
- `ws/.lgwf/wf_audit_fix/result_summary.json`

## 验证

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\wf-audit-fix\wf\workflow.lgwf
python -m unittest discover skills\wf-audit-fix\tests
```

## 禁止事项

- 不在 package 根目录生成可运行 `workflow.lgwf`
- 不生成孙级 workflow
- 不把运行态 `.lgwf` 写入源码树
- 不把 `lgwf-wf-prompt-fix`、自动重试、自动回滚或 `lgwf-wf-tools` registry 自动注册混入当前 skill
