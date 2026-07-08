# Candidate 修复循环规范

- 只允许修改 `.lgwf/wf_audit_fix/runtime_context.json` 中 `candidate_workspace_plan.candidate_package_root` 指向的 candidate 副本目录。
- 只修复静态 DSL、路径、资源引用和 `audit` 可见问题。
- 不得运行目标 workflow 业务，不得写入真实目标目录。
- `AGENT_LOOP` 的 CODEX slot 不接收目标目录或目标文件参数；所有可写范围必须从上下文 JSON 中读取并自行校验。
- 若当前证据不足以安全修复，优先缩小修改范围并保留待补齐点。
