from typing import Any


def raise_on_failed_result(capability: str, node_id: str, result: dict[str, Any]) -> None:
    if result.get("ok") is not False:
        return
    exit_code = result.get("exit_code")
    stderr = _compact(result.get("stderr"))
    stdout = _compact(result.get("stdout"))
    details = [f"{capability} node '{node_id}' failed"]
    if exit_code is not None:
        details.append(f"exit_code={exit_code}")
    if stderr:
        details.append(f"stderr={stderr}")
    elif stdout:
        details.append(f"stdout={stdout}")
    raise RuntimeError("; ".join(details))


def _compact(value: Any, max_length: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.strip().split())
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text
