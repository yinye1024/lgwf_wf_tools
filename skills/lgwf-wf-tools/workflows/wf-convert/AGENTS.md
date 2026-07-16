# lgwf-wf-convert 工作流指引

本目录是 `lgwf-wf-tools/workflows/wf-convert` 下的内部 workflow package，由 facade 根目录 `registry.json` 派发，不作为独立 Codex skill 注册。

## 模块契约

- 模块类型：`lgwf_workflow_package`。
- 执行前必须读取 `../01-share/module-contract.md`、`../01-share/registry-contract.md`、`../01-share/lgwf-dispatch.md`、`../01-share/lgwf-monitor.md`、`../01-share/approval.md` 和 `../01-share/artifacts.md`。
- 入口字段、输入示例和 `--auto-human` 策略以本目录 `entry_contract.json` 为准；本文件只解释业务纪律和运行边界。
- 转换输出交给 `wf-create-fast` 和主 agent 时，目标模块必须继续满足 `module-contract.md` 的自包含契约。

## 目标

`wf-convert` 面向 prompt workflow 转换场景：读取现有 prompt workflow 目录，分析 prompt、agent、resource 和说明文件，产出可交给 `wf-create-fast` 的创建输入包、源业务契约和转换映射。

`wf-convert` 不在自身流程内完成最终目标 LGWF workflow 实现，也不直接启动下游创建 workflow。转换输入通过人工确认后，它生成 `wf-create-fast` 的输入并 HANDOFF 给主 agent；主 agent 负责启动 `wf-create-fast`。`wf-convert` 不自动调用标准创建实现链路、`wf-prompt-fix`、`wf-prompt-upgrade`、`wf-fix` 或 `wf-post-fix`。

`wf-convert` 先通过 `prepare_wf_create_fast_payload` 生成 `wf-create-fast` 的输入，其中 `source_root` 会映射为 `request.target_dir`，作为下游创建阶段可读取的只读资料目录；再通过 `map_wf_create_fast_input` 把 `state.lgwf_wf_convert.wf_create_fast_payload` 映射为 `state.lgwf_wf_convert.wf_create_fast_input`。最后 `prepare_wf_create_fast_handoff` 写入 `.lgwf/wf_create_fast_handoff.json`，`HANDOFF handoff_to_wf_create_fast` 交给主 agent 启动 `wf-create-fast`。

## 目录边界

- 真实 workflow package root：`wf/`
- workflow 入口：`wf/workflow.lgwf`
- work dir：`ws/`
- 运行状态只允许写入 `ws/.lgwf`
- 目标 package 根目录不得写入 `.lgwf`

## 输入契约

推荐输入：

```json
{
  "prompt_convert_target": {
    "target_dir": "skills/example-prompt-workflow",
    "entry_files": ["README.md"],
    "target_workflow_name": "example-workflow",
    "target_package_root": "skills/example-workflow"
  }
}
```

## 固定产物

- `.lgwf/prompt_convert_target.json`
- `.lgwf/prompt_file_index.json`
- `.lgwf/prompt_workflow_inspection.json`
- `.lgwf/wf_create_fast_input_proposal.json`
- `.lgwf/wf_create_fast_input_approval.json`
- `.lgwf/wf_create_fast_input.json`
- `.lgwf/wf_create_fast_payload.json`
- `.lgwf/wf_create_fast_input_for_wf_create_fast.json`
- `.lgwf/wf_create_fast_handoff.json`
- `state.lgwf_wf_convert.wf_create_fast_input`
- `state.lgwf_wf_convert.wf_create_fast_handoff_payload`
- `state.lgwf_wf_convert.wf_create_fast_handoff`

## 下游 `wf-create-fast`

转换完成后，`wf-convert` handoff payload 要求主 agent 使用：

- workflow id：`wf-create-fast`
- workflow：`workflows/wf-create-fast/wf/workflow.lgwf`
- work dir：`workflows/wf-create-fast/ws`
- input file：`.lgwf/wf_create_fast_input_for_wf_create_fast.json`

`wf-create-fast` 保留需求确认、业务流确认、scaffold 落盘和主 agent handoff 边界，不生成 `step_designs.json`，也不调用标准创建实现链路。

`wf-convert` 传给 `wf-create-fast` 的输入保持 `raw_intent` 入口形态，同时在可用时附带 `source_business_contract`、`conversion_mapping` 和 `prompt_workflow_context`。`source_root` 会作为 `request.target_dir` 传入，只表示创建 workflow 时可参考的源 prompt workflow 目录，不是目标 workflow 输出目录；目标输出目录仍由 `raw_intent`、需求确认和后续 `target_package_root` 确认收敛。

## Codex 节点监控约束

`inspect_prompt_workflow_react` 和 `propose_create_input_react` 包含多个 Codex slot，可能在等待模型首包、读取源文件或写出 stdout 期间短时间没有 token live status 更新。

- `codex token-status` 中 `total_tokens=0`、`seconds_since_update` 增大或 `turn_count=0` 不能单独作为失败依据。
- 节点未达到自身 `timeout_seconds` 前，主 agent 不得自行判定失败，不得停止、重启、跳过或手工补写 `.lgwf/` 中间产物。
- 疑似无进展时只能提醒用户，并展示当前 `status`、后台 process log、Codex track dir 的 `metadata.json` / `stdout.txt` / `stderr.txt`、目标产物是否存在和后台 `pid` 是否仍存在。
- 只有 process log 出现 `node failed`、track dir `metadata.json` 中 `exit_code` 非 0、`timed_out=true`，或后台进程已退出且没有节点完成记录和目标产物时，才可按失败处理。

## 最小验证

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-convert\tests
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-convert\wf\workflow.lgwf
```
