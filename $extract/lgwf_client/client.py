from collections.abc import Iterable

import lgwf_client.types as client_types
import lgwf_client.runners.types as runner_types


class LocalClient:
    def __init__(
        self,
        runners: Iterable[runner_types.Runner] | None = None,
    ) -> None:
        self._runners: dict[client_types.InstructionType, runner_types.Runner] = {}

        for runner in runners or []:
            instruction_type = runner.instruction_type

            if instruction_type in self._runners:
                raise ValueError(
                    f"Duplicate lgwf_client runner for instruction type: {instruction_type}"
                )

            self._runners[instruction_type] = runner

    def execute(self, instruction: client_types.Instruction) -> client_types.ExecutionResult:
        instruction_type = instruction["type"]
        runner = self._runners.get(instruction_type)

        if runner is None:
            raise NotImplementedError(
                "No lgwf_client runner registered for instruction type: "
                f"{instruction_type}"
            )

        return runner.run(instruction)

