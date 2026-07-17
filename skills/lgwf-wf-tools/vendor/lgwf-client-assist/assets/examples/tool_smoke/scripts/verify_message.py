import json
import pathlib
import sys


def main() -> int:
    execution_result = json.load(sys.stdin)
    if not isinstance(execution_result, dict) or execution_result.get("ok") is not True:
        raise RuntimeError("Codex execution result is missing or unsuccessful.")

    message_path = pathlib.Path("output/message.md")
    message = message_path.read_text(encoding="utf-8").strip()
    missing = [token for token in ("LGWF", "TOOL", "CODEX") if token not in message]
    if missing:
        raise RuntimeError(f"Generated message is missing required tokens: {', '.join(missing)}")

    print(
        json.dumps(
            {
                "verified": True,
                "path": message_path.as_posix(),
                "message": message,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
