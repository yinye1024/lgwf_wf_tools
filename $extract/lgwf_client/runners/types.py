from typing import Protocol

import lgwf_client.types as client_types


class Runner(Protocol):
    instruction_type: client_types.InstructionType

    def run(
        self,
        instruction: client_types.Instruction,
    ) -> client_types.ExecutionResult:
        ...

