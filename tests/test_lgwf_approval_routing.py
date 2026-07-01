import unittest

from lgwf.capabilities.flow.flow_human_approval import _route_for_response


class HumanApprovalRoutingTest(unittest.TestCase):
    def test_route_on_decision_accepts_legacy_value_decision(self) -> None:
        response = {
            "decision": "approve",
            "value": {
                "decision": "revise",
                "changes": ["调整仓库路径"],
                "comment": "用户要求修订范围。",
            },
        }

        self.assertEqual("revise", _route_for_response(response))


if __name__ == "__main__":
    unittest.main()
