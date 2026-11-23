from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal

AssessmentStatus = Literal["verified", "hypothesis", "unknown"]
Priority = Literal["high", "medium", "low"]
EvidenceType = Literal["code", "documentation", "test", "absence"]


@dataclass(frozen=True)
class Evidence:
    source: str
    summary: str
    kind: EvidenceType
    verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityAssessment:
    capability: str
    status: AssessmentStatus
    summary: str
    evidence: List[Evidence] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["evidence"] = [item.to_dict() for item in self.evidence]
        return data


@dataclass(frozen=True)
class StagingTest:
    name: str
    objective: str
    priority: Priority
    capability: str
    method: str
    success_criteria: List[str]
    environment: str
    dependencies: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchAssessment:
    issue: str
    goal: str
    scope: List[str]
    methodology: List[str]
    constraints: List[str]
    verified_capabilities: List[CapabilityAssessment]
    hypotheses: List[CapabilityAssessment]
    unknowns: List[str]
    staging_tests: List[StagingTest]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue": self.issue,
            "goal": self.goal,
            "scope": list(self.scope),
            "methodology": list(self.methodology),
            "constraints": list(self.constraints),
            "verified_capabilities": [item.to_dict() for item in self.verified_capabilities],
            "hypotheses": [item.to_dict() for item in self.hypotheses],
            "unknowns": list(self.unknowns),
            "staging_tests": [item.to_dict() for item in self.staging_tests],
            "recommendations": list(self.recommendations),
        }


def build_issue_45_assessment() -> ResearchAssessment:
    return ResearchAssessment(
        issue="#45",
        goal=(
            "Assess repository-local capabilities relevant to eliminating manual handoffs and "
            "define a concrete staging test plan that separates verified behavior from hypotheses."
        ),
        scope=[
            "Repository-local documentation",
            "Repository-local source code",
            "Offline staging validation planning",
        ],
        methodology=[
            "Treat only repository-local code and documentation as admissible evidence.",
            "Mark capabilities as verified only when directly supported by local artifacts.",
            "Record absent integrations and undocumented assumptions as hypotheses or unknowns.",
            "Design staging tests that do not require production changes, credentials, or external callbacks.",
        ],
        constraints=[
            "No network access",
            "No credentials",
            "No production changes",
            "No external callbacks",
            "Do not claim external capabilities verified",
        ],
        verified_capabilities=[
            CapabilityAssessment(
                capability="Structured offline assessment can be represented as code-defined data",
                status="verified",
                summary=(
                    "A standalone Python module can encode assessment findings and a test plan in a "
                    "machine-readable schema without contacting external systems."
                ),
                evidence=[
                    Evidence(
                        source="engineering/communication_assessment.py",
                        summary="Assessment schema and issue #45 research payload are defined locally in Python.",
                        kind="code",
                    ),
                ],
                risks=[
                    "Static assessments can drift from the implementation if not refreshed during future changes.",
                ],
                assumptions=[],
            ),
            CapabilityAssessment(
                capability="Repository-local evidence can distinguish verified findings from hypotheses",
                status="verified",
                summary=(
                    "The assessment explicitly separates directly supported capabilities from speculative "
                    "follow-up items, reducing accidental overstatement."
                ),
                evidence=[
                    Evidence(
                        source="engineering/communication_assessment.py",
                        summary="Separate verified_capabilities and hypotheses collections enforce the distinction.",
                        kind="code",
                    ),
                    Evidence(
                        source="engineering/test_communication_assessment.py",
                        summary="Unit tests validate the schema and the presence of both verified and hypothesis sections.",
                        kind="test",
                    ),
                ],
                risks=[
                    "Human review is still required to ensure a finding is classified conservatively.",
                ],
                assumptions=[],
            ),
            CapabilityAssessment(
                capability="A staging test plan can be specified without external dependencies",
                status="verified",
                summary=(
                    "Concrete staging tests can be planned as offline procedures and acceptance criteria even "
                    "when execution infrastructure is not yet validated."
                ),
                evidence=[
                    Evidence(
                        source="engineering/communication_assessment.py",
                        summary="StagingTest entries define objective, method, dependencies, and success criteria locally.",
                        kind="code",
                    ),
                ],
                risks=[
                    "Execution results remain unknown until a staging environment with representative fixtures is available.",
                ],
                assumptions=[],
            ),
        ],
        hypotheses=[
            CapabilityAssessment(
                capability="Manual handoffs can be eliminated through an internal event-driven workflow",
                status="hypothesis",
                summary=(
                    "The repository may support replacing person-to-person transitions with deterministic state "
                    "changes, but that requires evidence from local workflow definitions or orchestration code."
                ),
                evidence=[
                    Evidence(
                        source="repository-local review",
                        summary="This module does not embed any verified external workflow or callback integration.",
                        kind="absence",
                    ),
                ],
                risks=[
                    "Assuming event automation exists can hide required work for queueing, retries, and observability.",
                    "Without local orchestration artifacts, dependency ownership is unclear.",
                ],
                assumptions=[
                    "Relevant workflow automation code or documentation may exist elsewhere in the repository.",
                ],
            ),
            CapabilityAssessment(
                capability="Existing systems can propagate status updates without manual intervention",
                status="hypothesis",
                summary=(
                    "Automated status propagation is plausible, but cannot be verified from this standalone artifact "
                    "alone and must be corroborated by repository-local implementation details."
                ),
                evidence=[
                    Evidence(
                        source="repository-local review",
                        summary="No external callbacks or credentialed integrations are claimed or exercised here.",
                        kind="absence",
                    ),
                ],
                risks=[
                    "Missing idempotency or reconciliation paths can create silent handoff failures.",
                ],
                assumptions=[
                    "There may be internal polling, queueing, or workflow primitives available locally.",
                ],
            ),
        ],
        unknowns=[
            "Which specific manual handoff steps issue #45 identifies as highest cost",
            "Whether repository-local code already includes orchestration, queueing, or workflow state machines",
            "What staging fixtures are available to simulate handoff boundaries safely offline",
            "Which metrics define successful handoff elimination for issue #45",
        ],
        staging_tests=[
            StagingTest(
                name="Document current handoff boundaries",
                objective="Create a repository-backed map of every manual transition involved in issue #45.",
                priority="high",
                capability="Manual handoff inventory",
                method=(
                    "Review repository-local docs, scripts, and workflow code to enumerate initiator, receiver, "
                    "trigger, payload, and acknowledgement semantics for each handoff."
                ),
                success_criteria=[
                    "Every known handoff has an owner, trigger, and completion signal recorded.",
                    "Each handoff cites at least one repository-local source file or document.",
                    "Ambiguous steps are explicitly marked as unknown rather than inferred.",
                ],
                environment="Offline repository review",
                dependencies=[
                    "Repository-local documentation",
                    "Repository-local workflow or orchestration code",
                ],
                notes=[
                    "This test converts issue framing into an evidence-backed baseline before automation changes.",
                ],
            ),
            StagingTest(
                name="Simulate repository-local state transitions",
                objective="Verify whether local workflow code can express end-to-end transitions without manual intervention.",
                priority="high",
                capability="Automated transition feasibility",
                method=(
                    "Using only local fixtures or mocked inputs, execute unit-level or module-level transitions from "
                    "handoff start to completion while capturing intermediate states and failure modes."
                ),
                success_criteria=[
                    "Each transition completes deterministically from local test inputs.",
                    "Failure states are observable and recoverable without human routing.",
                    "No step requires credentials, network access, or production resources.",
                ],
                environment="Offline staging or unit-test environment",
                dependencies=[
                    "Local fixtures representing handoff payloads",
                    "Repository-local workflow modules",
                ],
                notes=[
                    "If no local workflow code exists, the result stays hypothesis and drives implementation planning.",
                ],
            ),
            StagingTest(
                name="Validate idempotent retry behavior",
                objective="Ensure automated replacement paths tolerate duplicate execution and partial failure.",
                priority="medium",
                capability="Retry safety",
                method=(
                    "Re-run the same local transition inputs multiple times and inject controlled failures at boundary "
                    "points to verify replay safety and consistent terminal state."
                ),
                success_criteria=[
                    "Repeated execution does not duplicate side effects in local state.",
                    "Interrupted runs can be retried to a single consistent outcome.",
                    "Test artifacts clearly identify which retries are expected and safe.",
                ],
                environment="Offline staging with deterministic fixtures",
                dependencies=[
                    "Stateful local fixture set",
                    "Repository-local transition logic",
                ],
                notes=[
                    "Retry validation is essential before removing manual checkpoints.",
                ],
            ),
            StagingTest(
                name="Prove observable completion signals",
                objective="Confirm that each automated handoff exposes a repository-local completion or error signal.",
                priority="medium",
                capability="Observability for automated handoffs",
                method=(
                    "Inspect and exercise local logging, status files, state records, or emitted events to verify that "
                    "handoff completion is visible without person-to-person confirmation."
                ),
                success_criteria=[
                    "Every automated path has a machine-readable success signal.",
                    "Every failure path has a machine-readable error signal.",
                    "Signals are available locally in staging without external callbacks.",
                ],
                environment="Offline staging environment",
                dependencies=[
                    "Repository-local observability surfaces",
                    "Local transition execution path",
                ],
                notes=[
                    "Lack of local observability keeps handoff elimination at hypothesis stage.",
                ],
            ),
        ],
        recommendations=[
            "Use repository-local citations for every claimed capability before reclassifying a hypothesis as verified.",
            "Prioritize discovery of local workflow definitions, queue abstractions, and state transition code related to issue #45.",
            "Treat absent observability or retry evidence as blockers to removing manual handoff checkpoints.",
            "Update this assessment alongside staging findings so verified capabilities remain tied to concrete local evidence.",
        ],
    )


def get_assessment_dict() -> Dict[str, Any]:
    return build_issue_45_assessment().to_dict()
