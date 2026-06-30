import importlib
import pathlib
import sys
from dataclasses import dataclass
from types import ModuleType


@dataclass(frozen=True)
class RuntimeSupport:
    wheel: pathlib.Path
    python: ModuleType
    file_ops: ModuleType
    process_execution: ModuleType
    timing: ModuleType
    json_io: ModuleType
    workspace_layout: ModuleType


def load_runtime_support(wheel: pathlib.Path) -> RuntimeSupport:
    return RuntimeSupport(
        wheel=wheel,
        python=_import_module_from_wheel("lgwf_client.python_execution", wheel, "lgwf_client"),
        file_ops=_import_module_from_wheel("lgwf_tools.file_ops", wheel, "lgwf_tools"),
        process_execution=_import_module_from_wheel("lgwf_client.process_execution", wheel, "lgwf_client"),
        timing=_import_module_from_wheel("lgwf_tools.timing", wheel, "lgwf_tools"),
        json_io=_import_module_from_wheel("lgwf_tools.json_io", wheel, "lgwf_tools"),
        workspace_layout=_import_module_from_wheel("lgwf_tools.workspace_layout", wheel, "lgwf_tools"),
    )


def _import_module_from_wheel(module_name: str, wheel: pathlib.Path, top_level: str) -> ModuleType:
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        wheel_text = str(wheel)
        if wheel_text not in sys.path:
            sys.path.insert(0, wheel_text)
        top_levels = {top_level}
        if module_name.startswith("lgwf_client."):
            top_levels.add("lgwf")
            top_levels.add("lgwf_tools")
        for name in list(sys.modules):
            if any(name == item or name.startswith(f"{item}.") for item in top_levels):
                del sys.modules[name]
        return importlib.import_module(module_name)
