import unittest

from lgwf.capabilities.flow.flow_human_approval import _route_for_response
from lgwf_client.main_agent.approvals import MISSING as APPROVAL_MISSING
from lgwf_client.main_agent.approvals import _controller_payload as approval_payload
from lgwf_client.main_agent.reviews import MISSING as REVIEW_MISSING
from lgwf_client.main_agent.reviews import _controller_payload as review_payload


class HumanApprovalRoutingTest(unittest.TestCase):
    def test_route_on_decision_ignores_approve_value(self) -> None:
        response = {
            "decision": "approve",
            "value": {
                "decision": "revise",
                "changes": ["调整仓库路径"],
                "comment": "用户要求修订范围。",
            },
        }

        self.assertEqual("approve", _route_for_response(response))

    def test_approval_approve_rejects_value_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "approve does not accept value-json"):
            approval_payload(
                request_id="human-123",
                decision="approve",
                value={},
                comment=None,
            )

    def test_approval_approve_accepts_decision_only(self) -> None:
        payload = approval_payload(
            request_id="human-123",
            decision="approve",
            value=APPROVAL_MISSING,
            comment=None,
        )

        self.assertEqual("approve", payload["decision"])
        self.assertNotIn("value", payload)

    def test_review_approve_rejects_value_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "approve route does not accept value-json"):
            review_payload(
                request_id="human-123",
                route="approve",
                value={"route": "approve"},
                comment=None,
            )

    def test_review_revise_requires_value_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "revise route requires value-json"):
            review_payload(
                request_id="human-123",
                route="revise",
                value=REVIEW_MISSING,
                comment=None,
            )

    def test_review_approve_accepts_decision_only(self) -> None:
        payload = review_payload(
            request_id="human-123",
            route="approve",
            value=REVIEW_MISSING,
            comment=None,
        )

        self.assertEqual("approve", payload["decision"])
        self.assertNotIn("value", payload)


if __name__ == "__main__":
    unittest.main()
