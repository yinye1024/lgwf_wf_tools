import json
from typing import Any

import lgwf.capabilities.exec.exec_state as exec_state_module
import lgwf.capabilities.exec.exec_result as exec_result_module
import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.types as capability_types
import lgwf.client_provider as client_provider_module
import lgwf_client.types as client_types


class ExecRunPythonCapability:
    name = "exec.run_python"

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        code = config.get("code")
        script_path = config.get("script_path")
        script_ref = config.get("script_ref")
        builtin_script = config.get("builtin_script")
        options = config.get("options")
        args = config.get("args", [])
        cwd = config.get("cwd")
        ref_root = config.get("ref_root")
        timeout_seconds = config.get("timeout_seconds", 300)
        instruction_path = config.get("instruction_path", "last_instruction")
        result_path = config.get("result_path", "last_result")
        state_updates_from_stdout = config.get("state_updates_from_stdout", False)

        has_code = isinstance(code, str) and bool(code.strip())
        has_script = isinstance(script_path, str) and bool(script_path.strip())
        has_script_ref = script_ref is not None
        has_builtin_script = builtin_script is not None

        if sum([has_code, has_script, has_script_ref, has_builtin_script]) != 1:
            raise ValueError("exec.run_python requires exactly one of config.code, config.script_path, config.script_ref, or config.builtin_script.")
        if builtin_script is not None and (not isinstance(builtin_script, str) or not builtin_script.strip()):
            raise ValueError("exec.run_python config.builtin_script must be a non-empty string.")
        if options is not None and not has_builtin_script:
            raise ValueError("exec.run_python config.options may only be used with config.builtin_script.")
        if options is not None and not isinstance(options, dict):
            raise ValueError("exec.run_python config.options must be an object.")
        if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
            raise ValueError("exec.run_python config.args must be a list of strings.")
        if ref_root is not None and not isinstance(ref_root, dict):
            raise ValueError("exec.run_python config.ref_root must be an object.")
        if cwd is not None and (not isinstance(cwd, str) or not cwd.strip()):
            raise ValueError("exec.run_python config.cwd must be a non-empty string.")
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("exec.run_python config.timeout_seconds must be a positive integer.")
        if not isinstance(instruction_path, str) or not instruction_path:
            raise ValueError("exec.run_python config.instruction_path must be a non-empty string.")
        if not isinstance(result_path, str) or not result_path:
            raise ValueError("exec.run_python config.result_path must be a non-empty string.")
        if not isinstance(state_updates_from_stdout, bool):
            raise ValueError("exec.run_python config.state_updates_from_stdout must be a boolean.")

        def node(state: capability_types.State) -> capability_types.State:
            payload: dict[str, Any] = {
                "args": args,
            }
            if has_code:
                payload["code"] = code
            elif has_script_ref:
                payload["script_ref"] = script_ref
            elif has_builtin_script:
                payload["builtin_script"] = builtin_script
                if options is not None:
                    payload["options"] = options
            else:
                payload["script_path"] = script_path

            instruction: client_types.Instruction = {
                "id": f"{node_id}:run_python",
                "type": "python",
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
            if cwd is not None:
                instruction["cwd"] = cwd
            if ref_root is not None:
                instruction["ref_root"] = ref_root

            client = self._client or client_provider_module.get_client()
            result = client.execute(instruction)
            exec_result_module.raise_on_failed_result(self.name, node_id, result)
            next_state = exec_state_module.public_state(state)
            next_state = flow_conditions_module.write_path(next_state, instruction_path, instruction)
            next_state = flow_conditions_module.write_path(next_state, result_path, result)
            if state_updates_from_stdout and result.get("ok"):
                next_state = self._apply_stdout_updates(next_state, result.get("stdout"))
            return next_state

        return node

    def _apply_stdout_updates(
        self,
        state: capability_types.State,
        stdout: Any,
    ) -> capability_types.State:
        if not isinstance(stdout, str) or not stdout.strip():
            return state
        try:
            updates = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ValueError("exec.run_python stdout state updates must be a JSON object.") from exc
        if not isinstance(updates, dict):
            raise ValueError("exec.run_python stdout state updates must be a JSON object.")

        next_state = state
        for path, value in updates.items():
            if not isinstance(path, str) or not path:
                raise ValueError("exec.run_python stdout state update keys must be non-empty string paths.")
            next_state = flow_conditions_module.write_path(next_state, path, value)
        return next_state


CAPABILITY = ExecRunPythonCapability()

