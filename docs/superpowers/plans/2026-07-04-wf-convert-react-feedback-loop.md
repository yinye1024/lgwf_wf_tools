# wf-convert ReAct 反馈闭环修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `wf-convert` 的 `propose_create_input_react` 在 `observe` 返回 `revise` 时，把失败点稳定回传给下一轮 `reason/act` 并可收敛，避免无意义多轮重跑。

**Architecture:** 保留现有 `REACT reason -> act -> observe -> decide` 结构，不改 runtime。修复点集中在 workflow 上下文、prompt 输出契约、`decide_create_input.py` 的确定性判断和回归测试，确保阻塞问题继续迭代，非阻塞问题交给人工确认。

**Tech Stack:** LGWF Authoring DSL、Python 标准库 `json/pathlib/unittest`、Markdown prompt。

---

## 文件结构

- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/wf/04_confirm_business_flow/workflow.lgwf`
  - 给 `propose_create_input_react` 的 `REASON` 增加上一轮 proposal 上下文。
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/wf/04_confirm_business_flow/agents/propose_observe.md`
  - 把 `issues` 固定为可执行结构：`field`、`blocking`、`issue`、`required_change`、`severity`。
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/wf/04_confirm_business_flow/agents/propose_reason.md`
  - 要求读取上一轮 `issues` 并输出 `issue_resolution_plan`。
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/wf/04_confirm_business_flow/agents/propose_act.md`
  - 要求按 `issue_resolution_plan` 定向修复，不重新发散。
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/wf/04_confirm_business_flow/scripts/decide_create_input.py`
  - 从单纯看 `verdict` 改为看确定性字段、路径合法性和 `blocking` issue。
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/tests/test_wf_script_flow_e2e.py`
  - 增加 `blocking=false` 不继续、`blocking=true` 继续、绝对 `source_root` 合法的脚本级测试。
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/tests/test_wf_runtime_fake_e2e.py`
  - 增加 “第一轮 observe revise，第二轮按反馈 pass” 的 fake runtime 测试。
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/README.md`
  - 记录 observe feedback 闭环规则和最小验证命令。

---

### Task 1: 为 decide_create_input 增加失败复现测试

**Files:**
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/tests/test_wf_script_flow_e2e.py`

- [ ] **Step 1: 写入 blocking issue 应继续的失败测试**

在 `test_case_decide_create_input_continue_on_gap` 后新增：

```python
    def test_case_decide_create_input_continue_on_blocking_issue(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/decide_create_input.py")
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / ".lgwf").mkdir()
            write_json(
                workdir / ".lgwf" / "wf_create_input_proposal.json",
                make_full_proposal(target_package_root="skills/lgwf-wf-tools/workflows/generated"),
            )
            write_json(
                workdir / ".lgwf" / "wf_create_input_observe.json",
                {
                    "verdict": "revise",
                    "issues": [
                        {
                            "field": "stages",
                            "blocking": True,
                            "issue": "缺少 evidence_strength，approval 无法原样确认",
                            "required_change": "为每个 stage 补充 evidence_strength",
                            "severity": "high",
                        }
                    ],
                },
            )
            result = run_script_main(module, workdir)
            self.assertEqual(result, {"next": "continue"})
```

- [ ] **Step 2: 写入非阻塞 issue 应退出到人工确认的失败测试**

继续新增：

```python
    def test_case_decide_create_input_exit_on_non_blocking_issue(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/decide_create_input.py")
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / ".lgwf").mkdir()
            write_json(
                workdir / ".lgwf" / "wf_create_input_proposal.json",
                make_full_proposal(target_package_root="skills/lgwf-wf-tools/workflows/generated"),
            )
            write_json(
                workdir / ".lgwf" / "wf_create_input_observe.json",
                {
                    "verdict": "revise",
                    "issues": [
                        {
                            "field": "run_workflow_notes_for_wf_create",
                            "blocking": False,
                            "issue": "建议在人工确认时关注剩余上下文",
                            "required_change": "交给 confirm_create_input 人工确认",
                            "severity": "low",
                        }
                    ],
                },
            )
            result = run_script_main(module, workdir)
            self.assertEqual(result, {"next": "exit"})
```

- [ ] **Step 3: 写入 source_root 绝对路径但 target_package_root 合法应退出的失败测试**

继续新增：

```python
    def test_case_decide_create_input_allows_absolute_source_root(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/decide_create_input.py")
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / ".lgwf").mkdir()
            proposal = make_full_proposal(target_package_root="skills/lgwf-wf-tools/workflows/generated")
            proposal["source_root"] = str((workdir / "source_prompt_workflow").resolve())
            write_json(workdir / ".lgwf" / "wf_create_input_proposal.json", proposal)
            write_json(
                workdir / ".lgwf" / "wf_create_input_observe.json",
                {"verdict": "pass", "issues": []},
            )
            result = run_script_main(module, workdir)
            self.assertEqual(result, {"next": "exit"})
```

- [ ] **Step 4: 运行测试确认失败**

Run:

```powershell
python -m unittest skills.lgwf-wf-tools.workflows.wf-convert.tests.test_wf_script_flow_e2e
```

Expected: 至少 `test_case_decide_create_input_exit_on_non_blocking_issue` 失败，因为当前脚本只要 `verdict=revise` 就继续。

---

### Task 2: 实现确定性 decide 逻辑

**Files:**
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/wf/04_confirm_business_flow/scripts/decide_create_input.py`

- [ ] **Step 1: 替换脚本实现**

将文件主体改为：

```python
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any


REQUIRED_FIELDS = (
    "workflow_name",
    "target_package_root",
    "raw_intent",
    "source_root",
    "stages",
    "prompt_contracts",
    "source_business_contract",
    "prompt_execution_mechanics",
    "presentation_constraints",
    "discarded_prompt_techniques",
    "conversion_mapping",
    "parity_requirements",
    "human_approval_points",
    "assumptions",
    "out_of_scope",
    "run_workflow_notes_for_wf_create",
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def has_valid_target_package_root(value: Any) -> bool:
    raw = str(value or "").strip()
    candidate = PurePosixPath(raw.replace("\\", "/"))
    if not raw or raw == ".":
        return False
    if candidate.is_absolute():
        return False
    if ":" in raw:
        return False
    if any(part == ".." for part in candidate.parts):
        return False
    if any(part == ".lgwf" for part in candidate.parts):
        return False
    return True


def has_required_payload_shape(proposal: dict[str, Any]) -> bool:
    if not all(field in proposal for field in REQUIRED_FIELDS):
        return False
    if not str(proposal.get("workflow_name", "")).strip():
        return False
    if not str(proposal.get("raw_intent", "")).strip():
        return False
    if not str(proposal.get("source_root", "")).strip():
        return False
    return has_valid_target_package_root(proposal.get("target_package_root"))


def has_blocking_issue(observe: dict[str, Any]) -> bool:
    issues = observe.get("issues", [])
    if not isinstance(issues, list):
        return True
    for issue in issues:
        if not isinstance(issue, dict):
            return True
        if issue.get("blocking") is True:
            return True
        if "blocking" not in issue and observe.get("verdict") != "pass":
            return True
    return False


def decide_next(proposal: dict[str, Any], observe: dict[str, Any]) -> str:
    if not has_required_payload_shape(proposal):
        return "continue"
    if observe.get("verdict") == "pass":
        return "exit"
    if has_blocking_issue(observe):
        return "continue"
    return "exit"


def main() -> None:
    root = Path.cwd()
    proposal = load_json(root / ".lgwf" / "wf_create_input_proposal.json")
    observe = load_json(root / ".lgwf" / "wf_create_input_observe.json")
    print(json.dumps({"next": decide_next(proposal, observe)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行脚本级测试确认通过**

Run:

```powershell
python -m unittest skills.lgwf-wf-tools.workflows.wf-convert.tests.test_wf_script_flow_e2e
```

Expected: `Ran ... tests` 且 `OK`。

---

### Task 3: 给 reason 回传上一轮 proposal

**Files:**
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/wf/04_confirm_business_flow/workflow.lgwf`

- [ ] **Step 1: 修改 REASON 上下文**

把 `propose_create_input_react` 的 `REASON CODEX` 段落从：

```lgwf
  REASON CODEX
    PROMPT "agents/propose_reason.md"
    CONTEXT workspace file ".lgwf/wf_create_input_observe.json"
    OUTPUT_JSON ".lgwf/wf_create_input_reason.json"
    RESULT state.lgwf_wf_convert.propose_reason_result
```

改为：

```lgwf
  REASON CODEX
    PROMPT "agents/propose_reason.md"
    CONTEXT workspace file ".lgwf/wf_create_input_observe.json"
    CONTEXT workspace file ".lgwf/wf_create_input_proposal.json"
    OUTPUT_JSON ".lgwf/wf_create_input_reason.json"
    RESULT state.lgwf_wf_convert.propose_reason_result
```

- [ ] **Step 2: 运行 DSL/脚本测试**

Run:

```powershell
python -m unittest skills.lgwf-wf-tools.workflows.wf-convert.tests.test_wf_script_flow_e2e
```

Expected: `OK`。

---

### Task 4: 结构化 observe issues

**Files:**
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/wf/04_confirm_business_flow/agents/propose_observe.md`

- [ ] **Step 1: 修改输出契约**

把输出示例改为：

```json
{
  "verdict": "revise",
  "issues": [
    {
      "field": "stages",
      "blocking": true,
      "severity": "high",
      "issue": "stage 缺少来源摘要或证据强度，approval 无法原样确认",
      "required_change": "为每个 stage 补充 source_files、source_summary 或 evidence_strength；若证据不足，降级到 assumptions"
    }
  ]
}
```

- [ ] **Step 2: 修改 Output Format 规则**

将 `issues` 规则改成以下文字：

```markdown
- `issues` 中每个对象必须包含 `field`、`blocking`、`severity`、`issue` 和 `required_change`。
- `blocking=true` 只用于会阻止人工确认、confirmed 原样复用或 payload 固化的问题。
- `blocking=false` 用于仍需人工关注但不会阻塞 `confirm_create_input` 的问题；这类问题不得导致 ReAct 继续迭代。
- `required_change` 必须是下一轮 `reason/act` 可执行的修改动作，不能只写“信息不足”。
- 如果 `verdict=revise` 但所有 issue 都是 `blocking=false`，`decide` 会退出到人工确认。
```

- [ ] **Step 3: 保留严格项但限定阻塞范围**

把“必须返回 `revise`”类描述调整为“阻塞 approval 或 payload 时必须 `blocking=true`；仅影响质量或人工判断便利性时使用 `blocking=false`”。例如：

```markdown
若 `stages` 或 `prompt_contracts` 缺少证据可见性，且 approval 无法原样确认，返回 `blocking=true`；若 proposal 已把证据不足降级到 `assumptions` 或 `run_workflow_notes_for_wf_create`，可返回 `blocking=false` 或 `pass`。
```

---

### Task 5: 要求 reason 生成 issue_resolution_plan

**Files:**
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/wf/04_confirm_business_flow/agents/propose_reason.md`

- [ ] **Step 1: 在输入中加入上一轮 proposal**

把输入列表改为：

```markdown
- `.lgwf/prompt_convert_target.json`：已确认转换目标。
- `.lgwf/prompt_workflow_inspection.json`：源 prompt workflow 分析结果。
- `.lgwf/wf_create_input_observe.json`：上一轮 proposal 审查结果。
- `.lgwf/wf_create_input_proposal.json`：上一轮 proposal；第一轮可能不存在或为空。
```

- [ ] **Step 2: 在任务中加入定向修复规则**

新增任务项：

```markdown
11. 如果上一轮 observe 包含 `blocking=true` 的 issues，本轮必须逐条生成 `issue_resolution_plan`，说明对应字段、修复动作、是否修改 proposal、无法确认时降级到 `assumptions`、`out_of_scope` 或 `run_workflow_notes_for_wf_create` 的规则。
12. 如果上一轮 proposal 已存在，本轮优先做最小定向修复，不重新设计无关字段。
```

- [ ] **Step 3: 修改输出示例**

把输出 JSON 示例扩展为：

```json
{
  "proposal_plan": [
    {
      "field": "raw_intent",
      "source": "prompt_convert_target + prompt_workflow_inspection",
      "construction_rule": "组织成 wf-create 可消费的自然语言意图"
    }
  ],
  "issue_resolution_plan": [
    {
      "field": "stages",
      "blocking": true,
      "required_change": "为每个 stage 补充 source_files 和 evidence_strength",
      "resolution": "从 prompt_workflow_inspection.detected_stages 提取来源；证据不足的 stage 降级到 assumptions"
    }
  ],
  "fields_to_include": [
    "workflow_name",
    "target_package_root",
    "raw_intent",
    "source_root",
    "stages",
    "prompt_contracts",
    "source_business_contract",
    "prompt_execution_mechanics",
    "presentation_constraints",
    "discarded_prompt_techniques",
    "conversion_mapping",
    "parity_requirements",
    "human_approval_points",
    "assumptions",
    "out_of_scope",
    "run_workflow_notes_for_wf_create"
  ],
  "assumption_policy": "无法确认的内容必须进入 assumptions",
  "known_limits": []
}
```

- [ ] **Step 4: 修改 Output Format**

加入：

```markdown
- JSON 顶层字段固定为 `proposal_plan`、`issue_resolution_plan`、`fields_to_include`、`assumption_policy` 和 `known_limits`。
- `issue_resolution_plan` 必须覆盖上一轮所有 `blocking=true` issues；第一轮没有上一轮 proposal 或没有 blocking issue 时输出空数组。
```

---

### Task 6: 要求 act 按修复计划最小修改

**Files:**
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/wf/04_confirm_business_flow/agents/propose_act.md`

- [ ] **Step 1: 修改输入说明**

将输入列表改为：

```markdown
- `.lgwf/prompt_convert_target.json`
- `.lgwf/prompt_workflow_inspection.json`
- `.lgwf/wf_create_input_reason.json`
- `.lgwf/wf_create_input_proposal.json`：上一轮 proposal；第一轮可能不存在或为空。
```

- [ ] **Step 2: 加入最小修复约束**

在生成规则中加入：

```markdown
- 如果 `wf_create_input_reason.json` 包含非空 `issue_resolution_plan`，本轮必须优先按该计划修复上一轮 proposal；未被 issue 指向且仍然有效的字段应保持语义稳定，避免无关重写。
- 对 `blocking=true` issue，必须在对应字段、`assumptions`、`out_of_scope` 或 `run_workflow_notes_for_wf_create` 中体现修复结果；不能只在自然语言里解释。
- 如果某个 required_change 无法从 inspection 证据中确认，必须把该项降级到 `assumptions` 或 `run_workflow_notes_for_wf_create`，并避免写入确定事实字段。
```

---

### Task 7: 增加 fake runtime 两轮收敛测试

**Files:**
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/tests/test_wf_runtime_fake_e2e.py`

- [ ] **Step 1: 新增 scenario 映射**

在 fake prompt mapping 中新增场景 `observe_revise_then_pass`，第一轮 `propose_observe` 返回：

```python
{
    "verdict": "revise",
    "issues": [
        {
            "field": "stages",
            "blocking": True,
            "severity": "high",
            "issue": "stage 缺少 evidence_strength，approval 无法原样确认",
            "required_change": "为每个 stage 补充 evidence_strength",
        }
    ],
}
```

第二轮 `propose_reason` 返回包含：

```python
{
    "proposal_plan": [{"field": "stages", "source": "previous proposal + observe issue"}],
    "issue_resolution_plan": [
        {
            "field": "stages",
            "blocking": True,
            "required_change": "为每个 stage 补充 evidence_strength",
            "resolution": "已在 stage 条目中补充 high confidence 证据说明",
        }
    ],
    "fields_to_include": list(proposal_second.keys()),
    "assumption_policy": "证据不足时降级到 assumptions",
    "known_limits": [],
}
```

第二轮 `propose_act` 返回的 `stages` 至少包含：

```python
{
    "name": "分析源 prompt workflow",
    "responsibility": "索引 prompt 文件并整理可交给 wf-create 的输入方案",
    "inputs": ["prompt_convert_target", "prompt_file_index"],
    "outputs": ["wf_create_input_proposal"],
    "source_files": ["README.md", "flow/workflow.lgwf"],
    "source_summary": "来自源 README 和 workflow.lgwf 的阶段职责",
    "evidence_strength": "high",
}
```

第二轮 `propose_observe` 返回：

```python
{"verdict": "pass", "issues": []}
```

- [ ] **Step 2: 新增测试方法**

新增：

```python
    def test_observe_revise_then_pass(self) -> None:
        scenario = {
            "scenario_id": "observe_revise_then_pass",
            "approval_steps": [
                {
                    "approval_node": "collect_prompt_workflow_target",
                    "submit_value": {
                        "target_dir": "<temp_fixture_root>/sample_prompt_workflow",
                        "entry_files": ["README.md", "flow/workflow.lgwf"],
                        "target_workflow_name": "demo-converted-workflow",
                        "target_package_root": "skills/lgwf-wf-tools/workflows/generated/demo-converted-workflow",
                        "constraints": ["不直接生成最终 LGWF workflow", "不自动调用 wf-create"],
                    },
                },
                {
                    "approval_node": "confirm_create_input",
                    "submit_value": {
                        "approval": "approve",
                        "comment": "observe revise 后第二轮已修复",
                    },
                },
            ],
        }
        work_dir, phase_history, call_log, approval_events = self.run_scenario(scenario)
        self.assertEqual(phase_history[-1]["phase"], "completed")
        self.assert_artifacts(work_dir, scenario["scenario_id"])
        self.assert_prompt_call_counts(
            call_log,
            {
                "wf/04_confirm_business_flow/agents/inspect_reason.md": 1,
                "wf/04_confirm_business_flow/agents/inspect_act.md": 1,
                "wf/04_confirm_business_flow/agents/inspect_observe.md": 1,
                "wf/04_confirm_business_flow/agents/propose_reason.md": 2,
                "wf/04_confirm_business_flow/agents/propose_act.md": 2,
                "wf/04_confirm_business_flow/agents/propose_observe.md": 2,
            },
        )
        proposal = read_utf8_json(work_dir / ".lgwf" / "wf_create_input_proposal.json")
        self.assertEqual(proposal["stages"][0]["evidence_strength"], "high")
```

- [ ] **Step 3: 运行 fake runtime 测试**

Run:

```powershell
python -m unittest skills.lgwf-wf-tools.workflows.wf-convert.tests.test_wf_runtime_fake_e2e
```

Expected: `OK`。

---

### Task 8: 更新文档和最终验证

**Files:**
- Modify: `skills/lgwf-wf-tools/workflows/wf-convert/README.md`

- [ ] **Step 1: 在 README 增加反馈闭环说明**

在“运行状态”后新增：

```markdown
## ReAct 反馈闭环

`propose_create_input_react` 的 `observe` 必须输出结构化 `issues`。每个 issue 包含 `blocking`：

- `blocking=true`：会阻塞人工确认、confirmed 原样复用或 payload 固化，`decide_create_input.py` 会继续下一轮 ReAct。
- `blocking=false`：只影响人工关注或后续运行质量，`decide_create_input.py` 会退出到 `confirm_create_input`，由人工确认处理。

下一轮 `reason` 同时读取 `.lgwf/wf_create_input_observe.json` 和 `.lgwf/wf_create_input_proposal.json`，必须生成 `issue_resolution_plan`。`act` 按该计划最小修复上一轮 proposal，避免无关重写。
```

- [ ] **Step 2: 运行完整 wf-convert 测试**

Run:

```powershell
python -m unittest discover skills\lgwf-wf-tools\workflows\wf-convert\tests
```

Expected: `OK`。

- [ ] **Step 3: 运行 workflow audit**

Run:

```powershell
python skills\lgwf-wf-tools\vendor\lgwf-client-assist\scripts\lgwf.py audit skills\lgwf-wf-tools\workflows\wf-convert\wf\workflow.lgwf
```

Expected: audit 通过，不出现 `propose_create_input_react` DSL 错误。

- [ ] **Step 4: 检查工作区差异**

Run:

```powershell
git diff -- skills/lgwf-wf-tools/workflows/wf-convert docs/superpowers/plans/2026-07-04-wf-convert-react-feedback-loop.md
```

Expected: diff 只包含本计划涉及的 workflow、prompt、脚本、测试和 README。

---

## 风险和验收标准

- `observe` 仍可严格，但必须区分阻塞与非阻塞，避免把人工可判断的问题变成自动循环。
- `source_root` 允许绝对路径；`target_package_root` 继续严格限制为工作区相对路径。
- 第二轮 `reason` 必须同时看到上一轮 observe 和上一轮 proposal，否则只能重新生成，不能稳定 patch。
- 验收通过条件：
  - blocking issue 触发下一轮。
  - non-blocking issue 退出到人工确认。
  - observe revise 后第二轮可 pass。
  - 现有 happy path 和 revise-then-approve 仍通过。
