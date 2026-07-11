# repo-context-pack

`repo-context-pack` 用来扫描指定仓库或模块目录，生成 AI agent 接手任务前最需要的上下文包。它适合 onboarding、modification、review、workflow-authoring 和 handoff 场景。

## 快速使用

```powershell
python skills\repo-context-pack\scripts\build_context_pack.py `
  --target-dir D:\path\to\repo `
  --output-dir D:\path\to\repo\.local\context-packs\repo `
  --focus workflow-authoring `
  --depth normal
```

也可以用 LGWF runtime 运行内嵌 workflow；运行状态放在 `skills/repo-context-pack/ws/.lgwf/`：

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py run `
  --workflow-lgwf skills\repo-context-pack\wf\workflow.lgwf `
  --work-dir skills\repo-context-pack\ws `
  --input-json-file request.json
```

`request.json` 示例：

```json
{
  "target_dir": "D:/allen/github/lgwf_wf_tools",
  "output_dir": "D:/allen/github/lgwf_wf_tools/.local/context-packs/lgwf_wf_tools",
  "focus": "workflow-authoring",
  "depth": "normal",
  "max_files": 1600
}
```

## 工作流阶段

- `entry_scope_resolution`：归一化输入，确认只读目标目录和输出目录。
- `target_context_inventory`：识别入口文件、模块地图、命令和风险候选。
- `context_pack_rendering`：生成固定 Markdown 与 JSON 上下文包。
- `workflow_summary_handoff`：校验产物并写出运行摘要报告。

## 输出

输出目录包含：

- `repo_context_pack.md`
- `agent_handoff.md`
- `module_map.json`
- `command_inventory.json`
- `risk_register.md`
- `read_order.md`
- `summary.json`

## 验证

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\repo-context-pack\wf\workflow.lgwf
python -m unittest discover skills\repo-context-pack\tests
```

## 未覆盖范围

第一版不修复目标仓库问题，不生成目标测试，不注册 registry，不自动发布，不保证对大型 monorepo 做语义级完整理解。
