from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TOKEN_BUDGETS = {
    "capture_request_context": 120_000,
    "inspect_repo_state": 150_000,
    "identify_change_themes": 120_000,
    "compose_markdown_brief": 80_000,
    "present_brief": 40_000,
}


def infer_node_id(path: Path) -> str:
    name = path.parent.name
    marker = "_codex_prompt-"
    return name.split(marker, 1)[0] if marker in name else name


def load_metadata(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def collect_token_usage(root: Path = Path(".lgwf/codex")) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    if root.exists():
        for metadata_path in sorted(root.glob("*/metadata.json")):
            metadata = load_metadata(metadata_path)
            token_usage = metadata.get("token_usage", {})
            node_id = infer_node_id(metadata_path)
            total_tokens = int(token_usage.get("total_tokens", 0)) if isinstance(token_usage, dict) else 0
            budget = TOKEN_BUDGETS.get(node_id)
            nodes.append(
                {
                    "node_id": node_id,
                    "metadata_file": metadata_path.as_posix(),
                    "input_tokens": int(token_usage.get("input_tokens", 0)) if isinstance(token_usage, dict) else 0,
                    "cached_input_tokens": int(token_usage.get("cached_input_tokens", 0))
                    if isinstance(token_usage, dict)
                    else 0,
                    "output_tokens": int(token_usage.get("output_tokens", 0)) if isinstance(token_usage, dict) else 0,
                    "reasoning_output_tokens": int(token_usage.get("reasoning_output_tokens", 0))
                    if isinstance(token_usage, dict)
                    else 0,
                    "total_tokens": total_tokens,
                    "budget_total_tokens": budget,
                    "over_budget": bool(budget is not None and total_tokens > budget),
                    "timed_out": bool(metadata.get("timed_out", False)),
                }
            )
    totals = {
        "input_tokens": sum(item["input_tokens"] for item in nodes),
        "cached_input_tokens": sum(item["cached_input_tokens"] for item in nodes),
        "output_tokens": sum(item["output_tokens"] for item in nodes),
        "reasoning_output_tokens": sum(item["reasoning_output_tokens"] for item in nodes),
        "total_tokens": sum(item["total_tokens"] for item in nodes),
    }
    return {
        "nodes": nodes,
        "totals": totals,
        "over_budget_nodes": [item["node_id"] for item in nodes if item["over_budget"]],
    }


def main() -> None:
    report = collect_token_usage()
    output_path = Path(".lgwf/token_usage_by_node.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {
        "git_diff_brief.token_usage_by_node": report,
        "git_diff_brief.token_usage_by_node_result": {
            "ok": True,
            "output_file": ".lgwf/token_usage_by_node.json",
            "over_budget_nodes": report["over_budget_nodes"],
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
