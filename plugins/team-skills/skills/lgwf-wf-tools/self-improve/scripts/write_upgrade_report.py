from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SELF_IMPROVE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = SELF_IMPROVE_ROOT.parent
DEFAULT_OUTPUT_DIR = FACADE_ROOT / ".local" / "upgrade-reports"
LOCAL_ROOT = FACADE_ROOT / ".local"
VENDOR_MANIFEST = FACADE_ROOT / "vendor" / "lgwf-client-assist" / ".lgwf-client-assist-vendor.json"
ASSETS_ZIP = FACADE_ROOT / "assets" / "lgwf-client-assist.zip"
OVERRIDES_ROOT = LOCAL_ROOT / "overrides"
FORBIDDEN_OVERRIDE_TERMS = [
    "auto approve",
    "自动 approve",
    "跳过 approval",
    "skip approval",
    "direct write .response.json",
    "直接写 .response.json",
    "fallback 到用户 .codex",
    "fallback to user .codex",
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def read_vendor_manifest() -> dict[str, Any]:
    if not VENDOR_MANIFEST.is_file():
        return {"exists": False}
    data = json.loads(VENDOR_MANIFEST.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        return {"exists": True, "invalid": True}
    return {"exists": True, **data}


def override_findings() -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not OVERRIDES_ROOT.exists():
        return findings
    for path in sorted(OVERRIDES_ROOT.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append({"path": path.relative_to(FACADE_ROOT).as_posix(), "issue": "not UTF-8"})
            continue
        lowered = text.lower()
        for term in FORBIDDEN_OVERRIDE_TERMS:
            if term.lower() in lowered:
                findings.append(
                    {
                        "path": path.relative_to(FACADE_ROOT).as_posix(),
                        "issue": f"forbidden term: {term}",
                    }
                )
    return findings


def build_report(version: str, source: str) -> dict[str, Any]:
    preserved = {
        ".local/self-improve/incidents": count_files(LOCAL_ROOT / "self-improve" / "incidents"),
        ".local/self-improve/reports": count_files(LOCAL_ROOT / "self-improve" / "reports"),
        ".local/self-improve/proposals": count_files(LOCAL_ROOT / "self-improve" / "proposals"),
        ".local/self-improve/scorecards": count_files(LOCAL_ROOT / "self-improve" / "scorecards"),
        ".local/overrides": count_files(LOCAL_ROOT / "overrides"),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "source": source,
        "vendor_manifest": read_vendor_manifest(),
        "assets_zip_sha256": sha256_file(ASSETS_ZIP) if ASSETS_ZIP.is_file() else "",
        "local_root_exists": LOCAL_ROOT.exists(),
        "preserved_local_file_counts": preserved,
        "override_findings": override_findings(),
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# lgwf-wf-tools Upgrade Report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- version: `{report['version']}`",
        f"- source: `{report['source']}`",
        f"- local_root_exists: `{report['local_root_exists']}`",
        f"- assets_zip_sha256: `{report['assets_zip_sha256']}`",
        "",
        "## Vendor Manifest",
        "",
        "```json",
        json.dumps(report["vendor_manifest"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Preserved Local File Counts",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in report["preserved_local_file_counts"].items())
    lines.extend(["", "## Override Findings", ""])
    if report["override_findings"]:
        lines.extend(f"- `{item['path']}`: {item['issue']}" for item in report["override_findings"])
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="unknown")
    parser.add_argument("--source", default="manual")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_report(args.version, args.source)
    output_dir = Path(args.output_dir)
    base = output_dir / f"{utc_stamp()}-upgrade"
    write_json(base.with_suffix(".json"), report)
    write_markdown(base.with_suffix(".md"), report)
    print(json.dumps({"json": str(base.with_suffix(".json")), "md": str(base.with_suffix(".md"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
