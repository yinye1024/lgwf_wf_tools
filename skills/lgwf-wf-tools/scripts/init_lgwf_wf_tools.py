from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from doctor_lgwf_wf_tools import FACADE_ROOT, LGWF_PY, VENDOR_ROOT, run_doctor


ZIP_PATH = FACADE_ROOT / "assets" / "lgwf-client-assist.zip"
STATE_PATH = VENDOR_ROOT / ".lgwf-client-assist-vendor.json"
TEXT_SUFFIXES = {".json", ".md", ".py", ".txt", ".yaml", ".yml"}
LAST_INIT_PATH = FACADE_ROOT / ".local" / "init" / "last-init.json"
INSTALL_OUTPUT_TAIL_LIMIT = 4000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def write_state(zip_hash: str) -> None:
    STATE_PATH.write_text(
        json.dumps({"zip_sha256": zip_hash}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def normalize_extracted_root(temp_dir: Path) -> Path:
    direct = temp_dir / "lgwf-client-assist"
    if direct.is_dir():
        return direct
    children = [child for child in temp_dir.iterdir() if child.is_dir()]
    if len(children) == 1:
        return children[0]
    return temp_dir


def trim_trailing_blank_lines(client_root: Path) -> None:
    for path in client_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        normalized = text.rstrip("\r\n") + "\n"
        if normalized != text:
            path.write_text(normalized, encoding="utf-8")


def sanitize_vendor() -> list[str]:
    actions: list[str] = []
    skill_md = VENDOR_ROOT / "SKILL.md"
    if skill_md.is_file():
        skill_md.unlink()
        actions.append("removed_vendor_skill_md")

    assets_dir = VENDOR_ROOT / "assets"
    for runtime_state in ("install-state.json", "install-state.lock"):
        path = assets_dir / runtime_state
        if path.exists():
            path.unlink()
            actions.append(f"removed_{runtime_state}")

    if VENDOR_ROOT.exists():
        trim_trailing_blank_lines(VENDOR_ROOT)
    return actions


def refresh_vendor(zip_hash: str) -> list[str]:
    actions: list[str] = []
    if VENDOR_ROOT.exists():
        shutil.rmtree(VENDOR_ROOT)
        actions.append("removed_old_vendor")
    VENDOR_ROOT.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="lgwf-client-assist-") as raw_temp:
        temp_dir = Path(raw_temp)
        with zipfile.ZipFile(ZIP_PATH) as archive:
            archive.extractall(temp_dir)
        extracted = normalize_extracted_root(temp_dir)
        shutil.move(str(extracted), str(VENDOR_ROOT))
    actions.append("extracted_zip")

    actions.extend(sanitize_vendor())
    write_state(zip_hash)
    actions.append("wrote_vendor_hash")
    return actions


def summarize_install_output(text: str) -> dict[str, Any]:
    return {
        "length": len(text),
        "truncated": len(text) > INSTALL_OUTPUT_TAIL_LIMIT,
        "tail": text[-INSTALL_OUTPUT_TAIL_LIMIT:],
    }


def install_bundled_lgwf() -> dict[str, Any]:
    if not LGWF_PY.is_file():
        return {
            "passed": False,
            "skipped": True,
            "reason": "missing_lgwf_py",
            "lgwf_py": str(LGWF_PY),
        }

    scripts_dir = LGWF_PY.parent
    added_path = False
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
        added_path = True

    stdout = ""
    stderr_buffer = io.StringIO()
    install_error = ""
    returncode = 0
    wheel_replaced = False
    wheel = ""
    wheel_sha256 = ""
    bundled_version = ""
    installed_version = ""
    try:
        from lgwf_env_init import bootstrap as bootstrap_module
        from lgwf_env_init import install as install_module

        wheel_path = install_module.find_bundled_wheel(VENDOR_ROOT)
        support = bootstrap_module.load_runtime_support(wheel_path)
        wheel_replaced = install_module.ensure_bundled_lgwf(
            support,
            VENDOR_ROOT,
            force=False,
            stderr=stderr_buffer,
        )
        wheel = str(wheel_path)
        wheel_sha256 = sha256_file(wheel_path)
        bundled_version = str(support.python.wheel_version(wheel_path) or "")
        installed_version = str(support.python.installed_package_version("lgwf") or "")
    except Exception as exc:
        returncode = 1
        install_error = f"{type(exc).__name__}: {exc}"
        stderr_buffer.write(f"{install_error}\n")
    finally:
        if added_path:
            try:
                sys.path.remove(str(scripts_dir))
            except ValueError:
                pass

    install_state_path = VENDOR_ROOT / "assets" / "install-state.json"
    install_state = {}
    if install_state_path.is_file():
        try:
            data = json.loads(install_state_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                install_state = data
        except json.JSONDecodeError:
            install_state = {}
    install_report = {
        "wheel_replaced": wheel_replaced,
        "wheel": wheel or install_state.get("wheel", ""),
        "wheel_sha256": wheel_sha256 or install_state.get("wheel_sha256", ""),
        "bundled_version": bundled_version or install_state.get("bundled_version", ""),
        "installed_version": installed_version,
    }
    if install_error:
        install_report["error"] = install_error
    stderr = stderr_buffer.getvalue()
    return {
        "passed": returncode == 0,
        "skipped": False,
        "command": [sys.executable, str(LGWF_PY), "<internal-install-api>"],
        "returncode": returncode,
        "wheel_replaced": bool(wheel_replaced),
        "wheel": str(install_report.get("wheel") or ""),
        "wheel_sha256": str(install_report.get("wheel_sha256") or ""),
        "bundled_version": str(install_report.get("bundled_version") or ""),
        "installed_version": str(install_report.get("installed_version") or ""),
        "install_report": install_report,
        "install_state": install_state,
        "stdout": summarize_install_output(stdout),
        "stderr": summarize_install_output(stderr),
    }


def init_facade() -> dict[str, Any]:
    actions: list[str] = []
    zip_deleted = False
    zip_hash = ""

    if ZIP_PATH.is_file():
        zip_hash = sha256_file(ZIP_PATH)
        state = read_state()
        if state.get("zip_sha256") != zip_hash or not LGWF_PY.is_file() or (VENDOR_ROOT / "SKILL.md").exists():
            actions.extend(refresh_vendor(zip_hash))
            action = "imported"
        else:
            actions.extend(sanitize_vendor())
            action = "validated_existing_vendor"
        ZIP_PATH.unlink()
        zip_deleted = True
        actions.append("deleted_zip")
    else:
        actions.extend(sanitize_vendor())
        state = read_state()
        zip_hash = str(state.get("zip_sha256", ""))
        action = "noop"

    install = install_bundled_lgwf()
    if install.get("passed"):
        actions.append("installed_bundled_lgwf")

    doctor = run_doctor()
    return {
        "passed": bool(install["passed"]) and bool(doctor["passed"]),
        "action": action,
        "actions": actions,
        "facade_root": str(FACADE_ROOT),
        "client_root": str(VENDOR_ROOT),
        "lgwf_py": str(LGWF_PY),
        "zip_sha256": zip_hash,
        "zip_deleted": zip_deleted,
        "install": install,
        "doctor": doctor,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def write_last_init(result: dict[str, Any]) -> None:
    LAST_INIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_INIT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    result = init_facade()
    write_last_init(result)
    print(json.dumps(result, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"init_lgwf_wf_tools failed: {exc}", file=sys.stderr)
        raise
