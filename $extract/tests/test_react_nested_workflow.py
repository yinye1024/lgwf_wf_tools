import unittest

from lgwf.capabilities.subgraph.react.capability import SubgraphReactCapability


def python_slot(result_path: str, next_value: str | None = None) -> dict:
    assignments = {result_path: {"ok": True}}
    if next_value is None:
        pass
    else:
        assignments[result_path] = {"next": next_value}
        assignments["next"] = next_value
    return {
        "capability": "flow.assign",
        "config": {"assignments": assignments},
    }


class ReactNestedWorkflowTest(unittest.TestCase):
    def test_react_slot_accepts_and_runs_nested_workflow(self) -> None:
        config = {
            "max_steps": 1,
            "reason": python_slot("react_test.reason"),
            "act": {
                "capability": "subgraph.workflow",
                "config": {
                    "workflow": {
                        "entry_point": "validate",
                        "nodes": [
                            {
                                "id": "validate",
                                "capability": "flow.assign",
                                "config": {
                                    "assignments": {
                                        "react_test.act": {"validated": True},
                                    },
                                },
                            }
                        ],
                    }
                },
            },
            "observe": python_slot("react_test.observe"),
            "decide": python_slot("react_test.decide", "exit"),
        }

        node = SubgraphReactCapability().create_node("repair_loop", config)
        final_state = node({})

        self.assertEqual(final_state["react_test"]["act"], {"validated": True})
        self.assertEqual(final_state["react_test"]["decide"], {"next": "exit"})
        self.assertNotIn("__react__repair_loop__step", final_state)

    def test_react_slot_still_rejects_other_nested_subgraph_capabilities(self) -> None:
        config = {
            "max_steps": 1,
            "reason": python_slot("react_test.reason"),
            "act": {
                "capability": "subgraph.waterfall",
                "config": {"steps": [python_slot("react_test.act")]},
            },
            "observe": python_slot("react_test.observe"),
            "decide": python_slot("react_test.decide", "exit"),
        }

        with self.assertRaisesRegex(ValueError, "cannot use nested subgraph capability"):
            SubgraphReactCapability().create_node("repair_loop", config)


if __name__ == "__main__":
    unittest.main()
