from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from _paths import FACADE_ROOT, SELF_IMPROVE_ROOT
DEFAULT_PROPOSAL_DIR = FACADE_ROOT / ".local" / "self-improve" / "proposals"


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:48] or "proposal"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def render_proposal(topic: str, source_path: Path, source: dict[str, Any]) -> str:
    source_kind = "incident" if "summary" in source else "eval_report"
    summary = source.get("summary") or ("self eval failed" if not source.get("passed", True) else "self eval review")
    return "\n".join(
        [
            f"# Self Improve Proposal: {topic}",
            "",
            "## 证据",
            "",
            f"- source_kind: `{source_kind}`",
            f"- source_path: `{source_path}`",
            f"- summary: {summary}",
            "",
            "## 根因判断",
            "",
            f"- suspected_area: `{source.get('suspected_area', source.get('category', 'unknown'))}`",
            "- 需要人工复核具体根因；本文件只作为提案起点。",
            "",
            "## 拟修改范围",
            "",
            "- 候选文件：`AGENTS.md`、`registry.json`、相关 `workflows/*/AGENTS.md` 或 self eval case。",
            "- 不修改：`vendor/`、`.local/` 历史、目标 workflow 业务文件，除非用户另行批准。",
            "",
            "## 验证方式",
            "",
            "- `python workflows/self-improve/scripts/run_self_evals.py`",
            "- 如涉及内部 workflow，再运行对应 workflow package 的 audit 或 tests。",
            "",
            "## 风险",
            "",
            "- 可能影响 facade 路由、approval 或主 agent 监控行为。",
            "- 发布时必须保留 `.local/`，不要把本地历史写入发布包。",
            "",
            "## 决策",
            "",
            "- `approve`: 允许按本 proposal 进入普通修改流程。",
            "- `reject`: 不应用修改，只保留记录。",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--incident")
    group.add_argument("--eval-report")
    parser.add_argument("--topic")
    parser.add_argument("--output-dir", default=str(DEFAULT_PROPOSAL_DIR))
    args = parser.parse_args()

    source_path = Path(args.incident or args.eval_report)
    source = read_json(source_path)
    topic = args.topic or source.get("summary") or source.get("id") or "self-improve"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output = Path(args.output_dir) / f"{stamp}-{slugify(str(topic))}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_proposal(str(topic), source_path, source), encoding="utf-8")
    print(json.dumps({"proposal": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
