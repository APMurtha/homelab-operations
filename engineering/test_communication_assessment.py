import unittest

from engineering.communication_assessment import build_issue_45_assessment, get_assessment_dict


class CommunicationAssessmentTests(unittest.TestCase):
    def test_issue_and_constraints_are_present(self) -> None:
        assessment = build_issue_45_assessment()

        self.assertEqual(assessment.issue, "#45")
        self.assertIn("No network access", assessment.constraints)
        self.assertIn("Do not claim external capabilities verified", assessment.constraints)

    def test_verified_capabilities_are_all_marked_verified(self) -> None:
        assessment = build_issue_45_assessment()

        self.assertGreaterEqual(len(assessment.verified_capabilities), 1)
        self.assertTrue(all(item.status == "verified" for item in assessment.verified_capabilities))

    def test_hypotheses_are_separated_from_verified_capabilities(self) -> None:
        assessment = build_issue_45_assessment()

        self.assertGreaterEqual(len(assessment.hypotheses), 1)
        self.assertTrue(all(item.status == "hypothesis" for item in assessment.hypotheses))
        verified_names = {item.capability for item in assessment.verified_capabilities}
        hypothesis_names = {item.capability for item in assessment.hypotheses}
        self.assertTrue(verified_names.isdisjoint(hypothesis_names))

    def test_staging_tests_are_concrete_and_offline(self) -> None:
        assessment = build_issue_45_assessment()

        self.assertGreaterEqual(len(assessment.staging_tests), 3)
        for staging_test in assessment.staging_tests:
            self.assertTrue(staging_test.success_criteria)
            self.assertIn("Offline", staging_test.environment)
            self.assertNotIn("production", staging_test.method.lower())

    def test_dictionary_payload_has_expected_shape(self) -> None:
        payload = get_assessment_dict()

        self.assertEqual(payload["issue"], "#45")
        self.assertIn("verified_capabilities", payload)
        self.assertIn("hypotheses", payload)
        self.assertIn("staging_tests", payload)
        self.assertIsInstance(payload["verified_capabilities"], list)
        self.assertIsInstance(payload["hypotheses"], list)
        self.assertIsInstance(payload["staging_tests"], list)

    def test_verified_evidence_does_not_claim_external_capabilities(self) -> None:
        payload = get_assessment_dict()

        for capability in payload["verified_capabilities"]:
            text = " ".join([
                capability["capability"],
                capability["summary"],
                " ".join(item["summary"] for item in capability["evidence"]),
            ]).lower()
            self.assertNotIn("external callback verified", text)
            self.assertNotIn("production integration verified", text)


if __name__ == "__main__":
    unittest.main()
