# Facade WF Skill Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `docs/templates/facade-wf-skill-template/` 下新增可复用的 facade + registry + workflow contract 模板。

**Architecture:** 模板由说明文档、agent 迁移 prompt、可复制 skeleton、示例 `lgwf` workflow、示例 `tool-workflow`、校验脚本和模板结构测试组成。模板不复制任何业务 workflow 或 vendor runtime，只保留可迁移的接口和约束。

**Tech Stack:** Markdown、JSON、Python `unittest`、PowerShell 验证命令。

---

### Task 1: 模板结构测试

**Files:**
- Create: `docs/templates/facade-wf-skill-template/tests/test_template_structure.py`

- [ ] **Step 1: 写失败测试**

创建 `test_template_structure.py`，检查以下文件存在并可解析：

```python
from __future__ import annotations

import json
import unittest
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
SKELETON_ROOT = TEMPLATE_ROOT / "skeleton"


class FacadeWfSkillTemplateTests(unittest.TestCase):
    def test_required_template_files_exist(self) -> None:
        required = [
            "README.md",
            "agent-migration-prompt.md",
            "migration-guide.md",
            "adaptation-notes.md",
            "skeleton/SKILL.md",
            "skeleton/AGENTS.md",
            "skeleton/README.md",
            "skeleton/registry.json",
            "skeleton/docs/maintenance.md",
            "skeleton/docs/workflow-routing.md",
            "skeleton/docs/workflow-inputs.md",
            "skeleton/docs/facade-dispatch.md",
            "skeleton/workflows/01-share/module-contract.md",
            "skeleton/workflows/01-share/registry-contract.md",
            "skeleton/workflows/01-share/entry-contract.md",
            "skeleton/workflows/01-share/approval.md",
            "skeleton/workflows/01-share/artifacts.md",
            "skeleton/workflows/example-workflow/AGENTS.md",
            "skeleton/workflows/example-workflow/README.md",
            "skeleton/workflows/example-workflow/entry_contract.json",
            "skeleton/workflows/example-workflow/wf/workflow.lgwf",
            "skeleton/workflows/example-workflow/ws/.gitkeep",
            "skeleton/workflows/example-tool-workflow/AGENTS.md",
            "skeleton/workflows/example-tool-workflow/README.md",
            "skeleton/workflows/example-tool-workflow/entry_contract.json",
            "skeleton/workflows/example-tool-workflow/scripts/example_tool.py",
            "skeleton/scripts/list_workflows.py",
            "skeleton/scripts/validate_registry.py",
            "skeleton/scripts/run_skill_workflow.py",
            "skeleton/tests/test_registry_template.py",
        ]
        missing = [path for path in required if not (TEMPLATE_ROOT / path).is_file()]
        self.assertEqual(missing, [])

    def test_skeleton_registry_declares_lgwf_and_tool_workflow_examples(self) -> None:
        registry = json.loads((SKELETON_ROOT / "registry.json").read_text(encoding="utf-8"))
        workflows = {item["id"]: item for item in registry["workflows"]}
        self.assertEqual(set(workflows), {"example-workflow", "example-tool-workflow"})
        self.assertEqual(workflows["example-workflow"]["kind"], "lgwf")
        self.assertEqual(workflows["example-tool-workflow"]["kind"], "tool-workflow")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 确认测试失败**

Run:

```powershell
python docs\templates\facade-wf-skill-template\tests\test_template_structure.py -v
```

Expected: `FAIL`，缺失模板文件列表非空。

### Task 2: 新增 skeleton 与说明文档

**Files:**
- Create: `docs/templates/facade-wf-skill-template/README.md`
- Create: `docs/templates/facade-wf-skill-template/agent-migration-prompt.md`
- Create: `docs/templates/facade-wf-skill-template/migration-guide.md`
- Create: `docs/templates/facade-wf-skill-template/adaptation-notes.md`
- Create: `docs/templates/facade-wf-skill-template/skeleton/**`

- [ ] **Step 1: 新增模板根文档**

写入模板定位、适用场景、目录说明、复制方法和禁止事项。

- [ ] **Step 2: 新增 skeleton**

写入薄 `SKILL.md`、路由 `AGENTS.md`、`registry.json`、共享契约、示例 workflow、示例 tool-workflow、校验脚本和模板内测试。

- [ ] **Step 3: 新增 agent 迁移 prompt**

写入两段式迁移提示：先分析方案不改文件，再按确认方案分阶段实施。

### Task 3: 验证模板

**Files:**
- Test: `docs/templates/facade-wf-skill-template/tests/test_template_structure.py`
- Test: `docs/templates/facade-wf-skill-template/skeleton/tests/test_registry_template.py`

- [ ] **Step 1: 运行结构测试**

Run:

```powershell
python docs\templates\facade-wf-skill-template\tests\test_template_structure.py -v
```

Expected: `OK`。

- [ ] **Step 2: 运行 skeleton registry 测试**

Run:

```powershell
python docs\templates\facade-wf-skill-template\skeleton\tests\test_registry_template.py -v
```

Expected: `OK`。

- [ ] **Step 3: 解析 JSON**

Run:

```powershell
Get-Content docs\templates\facade-wf-skill-template\skeleton\registry.json -Encoding UTF8 -Raw | ConvertFrom-Json | Out-Null
Get-Content docs\templates\facade-wf-skill-template\skeleton\workflows\example-workflow\entry_contract.json -Encoding UTF8 -Raw | ConvertFrom-Json | Out-Null
Get-Content docs\templates\facade-wf-skill-template\skeleton\workflows\example-tool-workflow\entry_contract.json -Encoding UTF8 -Raw | ConvertFrom-Json | Out-Null
```

Expected: 三条命令均退出码为 `0`。
