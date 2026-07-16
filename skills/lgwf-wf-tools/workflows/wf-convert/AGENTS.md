# lgwf-wf-convert 工作流指引

本目录是 `lgwf-wf-tools/workflows/wf-convert` 下的内部 workflow package，由 facade 根目录 `registry.json` 派发，不作为独立 Codex skill 注册。

## 模块契约

- 模块类型：`lgwf_workflow_package`。
- 执行前必须读取 `../01-share/module-contract.md`、`../01-share/registry-contract.md`、`../01-share/lgwf-dispatch.md`、`../01-share/lgwf-monitor.md`、`../01-share/approval.md` 和 `../01-share/artifacts.md`。
- 入口字段、输入示例和 `--auto-human` 策略以本目录 `entry_contract.json` 为准；本文件只解释业务纪律和运行边界。
- 转换输出交给 `wf-create-fast` 和主 agent 时，目标模块必须继续满足 `module-contract.md` 的自包含契约。

## 目标

`wf-convert` 面向 prompt workflow 转换场景：读取现有 prompt workflow 目录，分析 prompt、agent、resource 和说明文件，产出可交给 `wf-create-fast` 的完整 handoff target file、源业务契约和转换映射。

`wf-convert` 不在自身流程内完成最终目标 LGWF workflow 实现，也不直接启动下游创建 workflow。转换输入通过人工确认后，它生成 `wf-create-fast` 的输入并 HANDOFF 给主 agent；主 agent 负责启动 `wf-create-fast`。`wf-convert` 不自动调用标准创建实现链路、`wf-prompt-fix`、`wf-prompt-upgrade`、`wf-fix` 或 `wf-post-fix`。

`wf-convert` 通过 `prepare_wf_create_fast_payload` 生成下游 handoff target file `.lgwf/wf_create_fast_handoff.json` 和启动输入 `.lgwf/wf_create_fast_launch_input.json`。target file 包含创建目标、业务契约、转换映射和 prompt workflow 上下文。`HANDOFF handoff_to_wf_create_fast` 交给主 agent 后，主 agent 先提交 handoff ack，再按 payload 中的 `input_json_file` 启动 `wf-create-fast`。

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
- `.lgwf/prompt_workflow_inspection_observe_py.json`
- `.lgwf/prompt_workflow_inspection_observe_codex.json`
- `.lgwf/prompt_workflow_inspection_observe.json`
- `.lgwf/wf_create_fast_input_proposal.json`
- `.lgwf/wf_create_fast_input_observe_py.json`
- `.lgwf/wf_create_fast_input_observe_codex.json`
- `.lgwf/wf_create_fast_input_observe.json`
- `.lgwf/wf_create_fast_input_confirmation_context.json`
- `.lgwf/wf_create_fast_input_approval.json`
- `.lgwf/wf_create_fast_input.json`
- `.lgwf/wf_create_fast_handoff.json`
- `state.lgwf_wf_convert.prompt_workflow_inspection_observe`
- `state.lgwf_wf_convert.wf_create_fast_input_observe`
- `state.lgwf_wf_convert.wf_create_fast_input_confirmation_context`
- `state.lgwf_wf_convert.wf_create_fast_input`
- `state.lgwf_wf_convert.wf_create_fast_handoff`

## ReAct 观察与判定边界

`inspect_prompt_workflow_react` 和 `propose_create_input_react` 都使用阶段内部质量门子 workflow 完成 `observe`：先由 Python 执行确定性结构、枚举、引用和覆盖检查，再由 Codex 只检查语义完整性，最后由 Python 合并为唯一 canonical observe。

- inspection canonical observe：`.lgwf/prompt_workflow_inspection_observe.json`
- proposal canonical observe：`.lgwf/wf_create_fast_input_observe.json`
- `decide_inspection.py` 和 `decide_create_input.py` 只能读取对应 canonical observe，不得读取业务产物或单个 observer 报告补充判断。
- canonical observe 缺失、schema 非法、阶段不匹配或结论自相矛盾时必须 fail closed，继续下一轮 ReAct。
- inspection 的非阻塞 issue 必须进入 proposal 的 `reason`；proposal 的非阻塞 issue 必须进入 `.lgwf/wf_create_fast_input_confirmation_context.json`，供人工确认查看。
- Python/Codex 中间报告用于诊断，不得作为父 workflow 的判定输入或对外状态契约。

## 下游 `wf-create-fast`

转换完成后，`wf-convert` handoff context 要求主 agent 使用：

- workflow id：`wf-create-fast`
- workflow：`workflows/wf-create-fast/wf/workflow.lgwf`
- work dir：`workflows/wf-create-fast/ws`
- target file：`.lgwf/wf_create_fast_handoff.json`

`wf-create-fast` 保留需求确认、业务流确认、scaffold 落盘和主 agent handoff 边界，不生成 `step_designs.json`，也不调用标准创建实现链路。

`wf-convert` 生成的 handoff target file 保持 `raw_intent` 入口形态，同时附带已确认的 `source_business_contract`、`conversion_mapping` 和 `prompt_workflow_context`。主 agent 启动 `wf-create-fast` 时，把该文件路径放入 `request.target_file`。

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
python skills\lgwf-wf-tools\scripts\doctor_lgwf_wf_tools.py --deep
```
