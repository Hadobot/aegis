from typing import List
import numpy as np


class ConfidenceScorer:
    def __init__(self):
        self.thresholds = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3
        }

    def calculate_input_confidence(
        self,
        similarity_scores: List[float],
        llm_certainty: float,
        evidence_count: int
    ) -> float:
        if not similarity_scores:
            return llm_certainty

        avg_similarity = np.mean(similarity_scores)
        max_similarity = np.max(similarity_scores)

        evidence_factor = min(evidence_count / 5, 1.0)

        confidence = (
            0.4 * max_similarity +
            0.3 * llm_certainty +
            0.2 * avg_similarity +
            0.1 * evidence_factor
        )

        return float(np.clip(confidence, 0.0, 1.0))

    def calculate_output_confidence(
        self,
        violations: List[str],
        severity_scores: List[float]
    ) -> float:
        if not violations:
            return 0.1

        violation_factor = min(len(violations) / 3, 1.0)

        severity_factor = 0.0
        if severity_scores:
            severity_factor = max(severity_scores)

        confidence = 0.6 * severity_factor + 0.4 * violation_factor

        return float(np.clip(confidence, 0.0, 1.0))

    def calculate_combined_risk(
        self,
        sentinel_confidence: float,
        shield_confidence: float,
        threat_type: str,
        violation_count: int
    ) -> float:
        combined = max(sentinel_confidence, shield_confidence)

        critical_threats = ["prompt_injection", "jailbreak"]
        if threat_type in critical_threats:
            combined *= 1.5

        if violation_count > 1:
            combined *= 1.2

        return float(np.clip(combined, 0.0, 1.0))

    def determine_action(self, combined_risk: float, threat_type: str) -> str:
        critical_threats = ["prompt_injection", "jailbreak"]

        if threat_type in critical_threats and combined_risk > 0.3:
            return "escalate"

        if combined_risk >= self.thresholds["high"]:
            return "block"
        elif combined_risk >= self.thresholds["medium"]:
            return "flag"
        elif combined_risk >= self.thresholds["low"]:
            return "escalate"
        else:
            return "allow"
