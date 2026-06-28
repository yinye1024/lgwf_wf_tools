import json
from typing import Any, TextIO


def dumps_public(data: Any, *, sort_keys: bool = True, indent: int | None = None) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=sort_keys, indent=indent)


def write_json_line(stream: TextIO, data: Any, *, sort_keys: bool = True) -> None:
    text = f"{dumps_public(data, sort_keys=sort_keys)}\n"
    try:
        stream.write(text)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "ascii"
        stream.write(text.encode(encoding, errors="backslashreplace").decode(encoding))


def parse_json_object(raw: str, label: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON.") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return data
