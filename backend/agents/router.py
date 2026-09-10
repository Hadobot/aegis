from typing import Dict, Any
from confidence.scoring import ConfidenceScorer
from confidence.thresholds import THRESHOLDS, CRITICAL_THREAT_TYPES


class Router:
    """
    ROUTER - The decision engine.
    Combines scores from Sentry and Shield, makes final decision.
    """

    def __init__(self):
        self.scorer = ConfidenceScorer()
        self.agent_id = "router"

    def decide(
        self,
        sentry_result: Dict[str, Any],
        shield_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        # 1. Extract scores
        sentry_confidence = sentry_result.get("confidence_score", 0)
        shield_confidence = shield_result.get("confidence_score", 0)
        threat_type = sentry_result.get("threat_type", "none")
        violation_count = len(shield_result.get("violations", []))

        # 2. Calculate combined risk
        combined_risk = self.scorer.calculate_combined_risk(
            sentinel_confidence=sentry_confidence,
            shield_confidence=shield_confidence,
            threat_type=threat_type,
            violation_count=violation_count
        )

        # 3. Determine action
        action = self.scorer.determine_action(combined_risk, threat_type)

        # 4. Generate reasoning
        reasoning = self._generate_reasoning(
            sentry_result, shield_result, combined_risk, action
        )

        return {
            "agent_id": self.agent_id,
            "combined_risk": combined_risk,
            "action": action,
            "reasoning": reasoning,
            "sentry_confidence": sentry_confidence,
            "shield_confidence": shield_confidence,
            "threat_type": threat_type,
            "violations": shield_result.get("violations", [])
        }

    def _generate_reasoning(
        self,
        sentry_result: Dict,
        shield_result: Dict,
        combined_risk: float,
        action: str
    ) -> str:
        parts = []

        if sentry_result.get("threat_detected"):
            parts.append(
                f"Sentry detected {sentry_result['threat_type']} "
                f"with {sentry_result['confidence_score']:.2f} confidence"
            )

        if shield_result.get("violations"):
            parts.append(
                f"Shield found {len(shield_result['violations'])} violations: "
                f"{', '.join(shield_result['violations'])}"
            )

        if not parts:
            parts.append("No threats or violations detected")

        parts.append(f"Combined risk: {combined_risk:.2f}")
        parts.append(f"Action: {action.upper()}")

        return ". ".join(parts)
