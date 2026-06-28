import pathlib
from collections.abc import Mapping

import lgwf_client.runners.python_runner.builtin_scripts.copy_directory as copy_directory_module
import lgwf_client.runners.python_runner.builtin_scripts.copy_file as copy_file_module
import lgwf_client.runners.python_runner.builtin_scripts.echo_args as echo_args_module
import lgwf_client.runners.python_runner.builtin_scripts.ensure_dir as ensure_dir_module
import lgwf_client.runners.python_runner.builtin_scripts.file_replace as file_replace_module
import lgwf_client.runners.python_runner.builtin_scripts.write_text_file as write_text_file_module


BUILTIN_SCRIPTS: Mapping[str, pathlib.Path] = {
    copy_directory_module.NAME: copy_directory_module.SCRIPT_PATH,
    copy_file_module.NAME: copy_file_module.SCRIPT_PATH,
    echo_args_module.NAME: echo_args_module.SCRIPT_PATH,
    ensure_dir_module.NAME: ensure_dir_module.SCRIPT_PATH,
    file_replace_module.NAME: file_replace_module.SCRIPT_PATH,
    write_text_file_module.NAME: write_text_file_module.SCRIPT_PATH,
}


def resolve_builtin_script(name: object) -> pathlib.Path:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("python instruction payload builtin_script must be a non-empty string.")

    try:
        path = BUILTIN_SCRIPTS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown python builtin_script: {name}") from exc

    if not path.is_file():
        raise ValueError(f"python builtin_script is not available: {name}")

    return path
