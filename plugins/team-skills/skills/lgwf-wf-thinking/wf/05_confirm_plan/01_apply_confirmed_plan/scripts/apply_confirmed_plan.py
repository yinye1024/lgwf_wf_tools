from __future__ import annotations

import importlib.util
from pathlib import Path


def main() -> None:
    target = Path(__file__).resolve().parents[2] / "scripts" / "apply_confirmed_plan.py"
    spec = importlib.util.spec_from_file_location("lgwf_wf_thinking_apply_confirmed_plan", target)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


if __name__ == "__main__":
    main()

