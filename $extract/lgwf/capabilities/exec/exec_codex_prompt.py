from typing import Any

import lgwf.capabilities.exec.exec_state as exec_state_module
import lgwf.capabilities.exec.exec_result as exec_result_module
import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.types as capability_types
import lgwf.client_provider as client_provider_module
import lgwf_client.types as client_types


class ExecCodexPromptCapability:
    name = "exec.codex_prompt"

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        prompt = config.get("prompt")
        prompt_ref = config.get("prompt_ref")
        spec_ref = config.get("spec_ref")
        context_refs = config.get("context_refs", [])
        target_dirs = config.get("target_dirs", [])
        target_files = config.get("target_files", [])
        target_dirs_path = config.get("target_dirs_path")
        target_files_path = config.get("target_files_path")
        output_json = config.get("output_json")
        cwd = config.get("cwd")
        ref_root = config.get("ref_root")
        mode = config.get("mode", "exec")
        args = config.get("args", [])
        model = config.get("model")
        foreground = config.get("foreground", False)
        timeout_seconds = config.get("timeout_seconds")
        instruction_path = config.get("instruction_path", "last_instruction")
        result_path = config.get("result_path", "last_result")

        has_prompt = isinstance(prompt, str) and bool(prompt.strip())
        has_prompt_ref = prompt_ref is not None
        if has_prompt == has_prompt_ref:
            raise ValueError("exec.codex_prompt requires exactly one of config.prompt or config.prompt_ref.")
        if spec_ref is not None:
            if not isinstance(spec_ref, dict):
                raise ValueError("exec.codex_prompt config.spec_ref must be an object when provided.")
            spec_path = spec_ref.get("path")
            if not isinstance(spec_path, str) or not spec_path.strip():
                raise ValueError("exec.codex_prompt config.spec_ref.path must be a non-empty string.")
        if mode != "exec":
            raise ValueError("exec.codex_prompt config.mode currently only supports 'exec'.")
        if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
            raise ValueError("exec.codex_prompt config.args must be a list of strings.")
        if model is not None and (not isinstance(model, str) or not model.strip()):
            raise ValueError("exec.codex_prompt config.model must be a non-empty string when provided.")
        if not isinstance(foreground, bool):
            raise ValueError("exec.codex_prompt config.foreground must be a boolean.")
        if not isinstance(context_refs, list):
            raise ValueError("exec.codex_prompt config.context_refs must be a list.")
        for index, item in enumerate(context_refs):
            if not isinstance(item, dict):
                raise ValueError(f"exec.codex_prompt config.context_refs[{index}] must be an object.")
            if item.get("type") not in {"file", "dir"}:
                raise ValueError(f"exec.codex_prompt config.context_refs[{index}].type must be 'file' or 'dir'.")
            raw_path = item.get("path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError(f"exec.codex_prompt config.context_refs[{index}].path must be a non-empty string.")
        static_target_dirs = self._validate_target_list(target_dirs, "target_dirs")
        static_target_files = self._validate_target_list(target_files, "target_files")
        if target_dirs_path is not None and (not isinstance(target_dirs_path, str) or not target_dirs_path):
            raise ValueError("exec.codex_prompt config.target_dirs_path must be a non-empty string when provided.")
        if target_files_path is not None and (not isinstance(target_files_path, str) or not target_files_path):
            raise ValueError("exec.codex_prompt config.target_files_path must be a non-empty string when provided.")
        if output_json is not None:
            if not isinstance(output_json, dict):
                raise ValueError("exec.codex_prompt config.output_json must be an object when provided.")
            output_json_path = output_json.get("path")
            if not isinstance(output_json_path, str) or not output_json_path.strip():
                raise ValueError("exec.codex_prompt config.output_json.path must be a non-empty string.")
            output_json_mode = output_json.get("mode", "managed")
            if output_json_mode not in {"managed", "file"}:
                raise ValueError("exec.codex_prompt config.output_json.mode must be 'managed' or 'file'.")
        if ref_root is not None and not isinstance(ref_root, dict):
            raise ValueError("exec.codex_prompt config.ref_root must be an object.")
        if cwd is not None and (not isinstance(cwd, str) or not cwd.strip()):
            raise ValueError("exec.codex_prompt config.cwd must be a non-empty string.")
        if timeout_seconds is not None and (not isinstance(timeout_seconds, int) or timeout_seconds <= 0):
            raise ValueError("exec.codex_prompt config.timeout_seconds must be a positive integer or null.")
        if not isinstance(instruction_path, str) or not instruction_path:
            raise ValueError("exec.codex_prompt config.instruction_path must be a non-empty string.")
        if not isinstance(result_path, str) or not result_path:
            raise ValueError("exec.codex_prompt config.result_path must be a non-empty string.")

        def node(state: capability_types.State) -> capability_types.State:
            payload: dict[str, Any] = {
                "mode": mode,
                "args": args,
                "foreground": foreground,
            }
            if model is not None:
                payload["model"] = model
            if has_prompt:
                payload["prompt"] = prompt
            else:
                payload["prompt_ref"] = prompt_ref
            if spec_ref is not None:
                payload["spec_ref"] = spec_ref
            if context_refs:
                payload["context_refs"] = context_refs
            effective_target_dirs = [
                *static_target_dirs,
                *self._state_target_list(state, target_dirs_path, "target_dirs_path"),
            ]
            effective_target_files = [
                *static_target_files,
                *self._state_target_list(state, target_files_path, "target_files_path"),
            ]
            if effective_target_dirs:
                payload["target_dirs"] = effective_target_dirs
            if effective_target_files:
                payload["target_files"] = effective_target_files
            if output_json is not None:
                payload["output_json"] = output_json

            instruction: client_types.Instruction = {
                "id": f"{node_id}:codex_prompt",
                "type": "codex",
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
            token_usage = self._token_usage(result)
            if token_usage is not None:
                next_state = flow_conditions_module.write_path(next_state, f"token_usage.{node_id}", token_usage)
            return next_state

        return node

    def _token_usage(self, result: dict[str, Any]) -> dict[str, int] | None:
        metadata = result.get("metadata")
        if not isinstance(metadata, dict):
            return None
        usage = metadata.get("token_usage")
        if not isinstance(usage, dict):
            return None
        normalized = {
            "input_tokens": self._non_negative_int(usage.get("input_tokens")),
            "output_tokens": self._non_negative_int(usage.get("output_tokens")),
            "total_tokens": self._non_negative_int(usage.get("total_tokens")),
            "cached_input_tokens": self._non_negative_int(usage.get("cached_input_tokens")),
            "reasoning_output_tokens": self._non_negative_int(usage.get("reasoning_output_tokens")),
        }
        if normalized["total_tokens"] == 0:
            normalized["total_tokens"] = normalized["input_tokens"] + normalized["output_tokens"]
        return normalized

    def _non_negative_int(self, value: Any) -> int:
        if isinstance(value, int | float) and value >= 0:
            return int(value)
        return 0

    def _validate_target_list(self, value: Any, label: str) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"exec.codex_prompt config.{label} must be a list.")
        targets: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"exec.codex_prompt config.{label}[{index}] must be a non-empty string.")
            targets.append(item)
        return targets

    def _state_target_list(self, state: capability_types.State, path: str | None, label: str) -> list[str]:
        if path is None:
            return []
        value = flow_conditions_module.read_path(state, path)
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"exec.codex_prompt config.{label} must resolve to a list.")
        targets: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"exec.codex_prompt config.{label}[{index}] must resolve to a non-empty string.")
            targets.append(item)
        return targets


CAPABILITY = ExecCodexPromptCapability()
