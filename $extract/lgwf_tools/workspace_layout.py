import pathlib


LGWF_DIR = ".lgwf"


def lgwf_dir(root: str | pathlib.Path) -> pathlib.Path:
    return pathlib.Path(root) / LGWF_DIR


def human_dir(root: str | pathlib.Path) -> pathlib.Path:
    return lgwf_dir(root) / "human"


def human_request_path(root: str | pathlib.Path, request_id: str) -> pathlib.Path:
    return human_dir(root) / f"{request_id}.request.json"


def human_response_path(root: str | pathlib.Path, request_id: str) -> pathlib.Path:
    return human_dir(root) / f"{request_id}.response.json"


def human_controller_payload_path(root: str | pathlib.Path, request_id: str) -> pathlib.Path:
    return human_dir(root) / f"{request_id}.controller_payload.json"


def human_codex_windows_dir(root: str | pathlib.Path) -> pathlib.Path:
    return human_dir(root) / "codex_windows"


def runs_dir(root: str | pathlib.Path) -> pathlib.Path:
    return lgwf_dir(root) / "runs"


def run_record_path(root: str | pathlib.Path, run_id: str) -> pathlib.Path:
    return runs_dir(root) / f"{run_id}.json"


def changed_files_path(root: str | pathlib.Path, run_id: str) -> pathlib.Path:
    return runs_dir(root) / f"{run_id}.changed_files.json"


def run_summary_path(root: str | pathlib.Path, run_id: str) -> pathlib.Path:
    return runs_dir(root) / f"{run_id}.summary.md"


def run_feedback_path(root: str | pathlib.Path, run_id: str) -> pathlib.Path:
    return runs_dir(root) / f"{run_id}.feedback.md"


def run_diff_path(root: str | pathlib.Path, run_id: str) -> pathlib.Path:
    return runs_dir(root) / f"{run_id}.diff.patch"


def processes_dir(root: str | pathlib.Path) -> pathlib.Path:
    return lgwf_dir(root) / "processes"


def codex_dir(root: str | pathlib.Path) -> pathlib.Path:
    return lgwf_dir(root) / "codex"


def codex_config_path(root: str | pathlib.Path) -> pathlib.Path:
    return codex_dir(root) / "config.json"


def logs_dir(root: str | pathlib.Path) -> pathlib.Path:
    return lgwf_dir(root) / "logs"


def runtime_log_path(root: str | pathlib.Path) -> pathlib.Path:
    return logs_dir(root) / "runtime.log"


def context_manifest_path(root: str | pathlib.Path) -> pathlib.Path:
    return lgwf_dir(root) / "context.json"
