import argparse
import contextlib
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import TextIO

from .bootstrap import RuntimeSupport


_DEFAULT_PACKAGE_PROFILE = {
    "profile": "dev",
    "install_policy": "always",
}
_PACKAGE_PROFILES = {
    "dev": "always",
    "prd": "version_mismatch",
}


def find_bundled_wheel(skill_root: pathlib.Path) -> pathlib.Path:
    wheels = sorted((skill_root / "assets").glob("lgwf-*.whl"))
    if not wheels:
        raise RuntimeError(f"missing bundled lgwf wheel under: {skill_root / 'assets'}")
    if len(wheels) > 1:
        raise RuntimeError(f"expected one bundled lgwf wheel, found {len(wheels)}")
    return wheels[0]


def write_doctor_report(args: argparse.Namespace, support: RuntimeSupport, stdout: TextIO) -> None:
    report = support.python.doctor_report(
        support.wheel,
        workflow_json=args.workflow_json,
        workflow_lgwf=args.workflow_lgwf,
        work_dir=args.work_dir,
    )
    for key, value in report.items():
        print(f"{key}={value}", file=stdout)


def ensure_lgwf_installed_timed(support: RuntimeSupport, force: bool, stderr: TextIO) -> None:
    timer = support.timing.Timer.start()
    ensure_lgwf_installed(support, force=force, stderr=stderr)
    print(f"[lgwf] startup step=install_lgwf duration_ms={timer.elapsed_ms()}", file=stderr)


def ensure_bundled_lgwf(
    support: RuntimeSupport,
    skill_root: pathlib.Path,
    *,
    force: bool,
    stderr: TextIO | None = None,
) -> bool:
    error_output = stderr or sys.stderr
    with _install_lock(skill_root, error_output):
        profile = load_package_profile(skill_root)
        target_version = support.python.wheel_version(support.wheel)
        installed_version = support.python.installed_package_version("lgwf")
        package_state = load_install_state(skill_root)
        wheel_sha256 = _file_sha256(support.wheel)
        reason = _install_reason(
            force=force,
            install_policy=profile["install_policy"],
            target_version=target_version,
            installed_version=installed_version,
            wheel_sha256=wheel_sha256,
            installed_wheel_sha256=package_state.get("wheel_sha256"),
            packaged_at=profile.get("packaged_at"),
            installed_at=package_state.get("installed_at"),
        )
        action = "skip" if reason in {"version_match", "wheel_hash_match"} else "force_reinstall"
        python_env = support.python.discover_python()
        print(
            f"[lgwf] install profile={profile['profile']} policy={profile['install_policy']} "
            f"action={action} reason={reason}",
            file=error_output,
        )
        print(f"[lgwf] install python={python_env.python_executable}", file=error_output)
        print(
            f"[lgwf] install wheel={support.wheel} sha256={wheel_sha256}",
            file=error_output,
        )
        print(
            f"[lgwf] install installed_before={installed_version or '<missing>'} "
            f"bundled_version={target_version or '<unknown>'}",
            file=error_output,
        )
        if profile.get("packaged_at"):
            print(
                f"[lgwf] install packaged_at={profile['packaged_at']} "
                f"recorded_installed_at={package_state.get('installed_at') or '<missing>'}",
                file=error_output,
            )
        if action == "skip":
            print("[lgwf] WHEEL_REPLACED=false", file=error_output)
            return False
        ensure_lgwf_installed(support, force=force, stderr=error_output)
        write_install_state(
            skill_root,
            {
                "installed_at": _utc_now_iso(),
                "packaged_at": profile.get("packaged_at") or "",
                "wheel": str(support.wheel),
                "wheel_sha256": wheel_sha256,
                "bundled_version": target_version or "",
            },
        )
        print("[lgwf] WHEEL_REPLACED=true", file=error_output)
        return True


def _install_reason(
    *,
    force: bool,
    install_policy: str,
    target_version: str | None,
    installed_version: str | None,
    wheel_sha256: str | None = None,
    installed_wheel_sha256: str | None = None,
    packaged_at: str | None = None,
    installed_at: str | None = None,
) -> str:
    if force:
        return "force_flag"
    if install_policy == "always":
        if (
            target_version
            and installed_version == target_version
            and wheel_sha256
            and installed_wheel_sha256 == wheel_sha256
        ):
            return "wheel_hash_match"
        if wheel_sha256 and installed_wheel_sha256 and installed_wheel_sha256 != wheel_sha256:
            return "wheel_hash_mismatch"
        return "policy_always"
    if not target_version:
        return "bundled_version_unknown"
    if installed_version != target_version:
        return "version_mismatch"
    return "version_match"


def _file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_package_profile(skill_root: pathlib.Path) -> dict[str, str]:
    path = skill_root / "assets" / "package-profile.json"
    if not path.is_file():
        return dict(_DEFAULT_PACKAGE_PROFILE)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid package profile: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid package profile: {path}")
    profile = payload.get("profile")
    install_policy = payload.get("install_policy")
    packaged_at = payload.get("packaged_at")
    if (
        not isinstance(profile, str)
        or profile not in _PACKAGE_PROFILES
        or install_policy != _PACKAGE_PROFILES[profile]
        or (packaged_at is not None and not isinstance(packaged_at, str))
    ):
        raise RuntimeError(f"invalid package profile: {path}")
    profile_data = {
        "profile": profile,
        "install_policy": install_policy,
    }
    if packaged_at:
        profile_data["packaged_at"] = packaged_at
    return profile_data


def load_install_state(skill_root: pathlib.Path) -> dict[str, str]:
    path = _install_state_path(skill_root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {key: value for key, value in payload.items() if isinstance(key, str) and isinstance(value, str)}


def write_install_state(skill_root: pathlib.Path, state: dict[str, str]) -> None:
    path = _install_state_path(skill_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(json.dumps(state, sort_keys=True, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _install_state_path(skill_root: pathlib.Path) -> pathlib.Path:
    return skill_root / "assets" / "install-state.json"


def _timestamp_at_or_after(installed_at: str | None, packaged_at: str | None) -> bool:
    installed_time = _parse_timestamp(installed_at)
    packaged_time = _parse_timestamp(packaged_at)
    return installed_time is not None and packaged_time is not None and installed_time >= packaged_time


def _parse_timestamp(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.UTC)
    return parsed.astimezone(datetime.UTC)


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


@contextlib.contextmanager
def _install_lock(skill_root: pathlib.Path, stderr: TextIO):
    lock_path = skill_root / "assets" / "install-state.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        print(f"[lgwf] install lock={lock_path}", file=stderr)
        _acquire_file_lock(lock_file)
        try:
            yield
        finally:
            _release_file_lock(lock_file)


def _acquire_file_lock(lock_file) -> None:
    if os.name == "nt":
        import msvcrt

        while True:
            try:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                time.sleep(0.05)
    else:
        import fcntl

        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)


def _release_file_lock(lock_file) -> None:
    if os.name == "nt":
        import msvcrt

        lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def ensure_lgwf_installed(
    support: RuntimeSupport,
    force: bool,
    stderr: TextIO | None = None,
) -> None:
    error_output = stderr or sys.stderr
    target_version = support.python.wheel_version(support.wheel)
    installed_version = support.python.installed_package_version("lgwf")

    print(
        f"[lgwf] replacing installed lgwf with bundled wheel: installed lgwf={installed_version or '<missing>'}, "
        f"bundled lgwf={target_version or '<unknown>'}, wheel={support.wheel}",
        file=error_output,
    )
    python_env = support.python.discover_python()
    command = python_env.module_command(
        "pip",
        ["install", "--upgrade", "--force-reinstall", "--no-deps", str(support.wheel)],
    )
    print(f"[lgwf] install command={subprocess.list2cmdline(command)}", file=error_output)
    result = support.python.ensure_package_installed(support.wheel, stderr=error_output)
    installed_after = support.python.installed_package_version("lgwf")
    print(
        f"[lgwf] install completed installed_after={installed_after or '<missing>'} "
        f"duration_ms={result.duration_ms}",
        file=error_output,
    )
