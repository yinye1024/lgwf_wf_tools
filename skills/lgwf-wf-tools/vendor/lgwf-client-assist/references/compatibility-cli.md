# LGWF 兼容 CLI

Agent 的常规入口是：

```powershell
python <skill-dir>\scripts\lgwf.py <command> ...
```

以下旧入口继续保留，参数、输出和退出码保持兼容，主要用于底层开发、测试和故障排查：

```powershell
python <skill-dir>\scripts\run_workflow.py ...
python -m lgwf_dsl.cli audit <workflow.lgwf>
python -m lgwf_dsl.cli compile <workflow.lgwf> -o <workflow.json>
python -m lgwf_client.cli --workflow-json <workflow.json> --work-dir <work_dir>
python -m lgwf_client.cli <command> ...
```

不要在新的 Agent 指南或业务 Skill 中把这些内部入口作为首选接口。
