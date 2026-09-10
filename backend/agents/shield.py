from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from rag.vector_store import ThreatVectorStore
from confidence.scoring import ConfidenceScorer
from typing import Dict, Any, List
import os
import json
import re


class ShieldAgent:
    """
    SHIELD - Validates LLM responses before delivery.
    Checks for data leakage, harmful content, policy violations.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("INTERNAL_LLM_MODEL", "google/gemini-2.0-flash-001"),
            api_key=os.getenv("INTERNAL_LLM_API_KEY") or os.getenv("UPSTREAM_LLM_API_KEY"),
            base_url=os.getenv("INTERNAL_LLM_BASE_URL", "https://openrouter.ai/api/v1"),
            temperature=0.0,
            max_tokens=500
        )
        self.vector_store = ThreatVectorStore()
        self.scorer = ConfidenceScorer()
        self.agent_id = "shield"

    async def validate_output(self, prompt: str, response: str) -> Dict[str, Any]:
        violations = []
        evidence = {}

        # 1. Check for data leakage
        leakage = await self._check_data_leakage(response)
        if leakage["detected"]:
            violations.append("data_leakage")
            evidence["leakage"] = leakage["evidence"]

        # 2. Check for harmful content
        harmful = await self._check_harmful_content(response)
        if harmful["detected"]:
            violations.append("harmful_content")
            evidence["harmful"] = harmful["evidence"]

        # 3. Check for PII exposure
        pii = self._check_pii_exposure(response)
        if pii["detected"]:
            violations.append("pii_exposure")
            evidence["pii"] = pii["evidence"]

        # 4. Check for system prompt leakage
        prompt_leak = await self._check_system_prompt_leakage(response)
        if prompt_leak["detected"]:
            violations.append("system_prompt_leakage")
            evidence["prompt_leak"] = prompt_leak["evidence"]

        # 5. Calculate confidence
        confidence = self.scorer.calculate_output_confidence(
            violations=violations,
            severity_scores=[0.8 if violations else 0.1]
        )

        return {
            "agent_id": self.agent_id,
            "violations": violations,
            "confidence_score": confidence,
            "severity": 0.9 if violations else 0.1,
            "evidence": evidence,
            "safe": len(violations) == 0
        }

    async def _check_data_leakage(self, response: str) -> Dict[str, Any]:
        leakage_patterns = [
            r"system prompt",
            r"api key",
            r"secret",
            r"password",
            r"token",
            r"credential"
        ]

        for pattern in leakage_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return {
                    "detected": True,
                    "evidence": f"Found potential data leakage: {pattern}"
                }

        return {"detected": False, "evidence": None}

    async def _check_harmful_content(self, response: str) -> Dict[str, Any]:
        system_prompt = """Analyze if this response contains harmful content:
        - Malicious code
        - Hate speech
        - Dangerous instructions
        - Illegal activities

        Respond with JSON: {"harmful": true/false, "reason": "..."}
        """

        try:
            result = await self.llm.ainvoke([
                HumanMessage(content=f"{system_prompt}\n\nResponse: {response[:500]}")
            ])
            parsed = json.loads(result.content)
            return {
                "detected": parsed.get("harmful", False),
                "evidence": parsed.get("reason", "")
            }
        except Exception:
            return {"detected": False, "evidence": None}

    def _check_pii_exposure(self, response: str) -> Dict[str, Any]:
        pii_patterns = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
            (r"\b\d{16}\b", "Credit Card"),
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email"),
            (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "Phone")
        ]

        for pattern, pii_type in pii_patterns:
            if re.search(pattern, response):
                return {
                    "detected": True,
                    "evidence": f"Found potential {pii_type}"
                }

        return {"detected": False, "evidence": None}

    async def _check_system_prompt_leakage(self, response: str) -> Dict[str, Any]:
        leak_indicators = [
            "my instructions are",
            "i was told to",
            "my system prompt",
            "i cannot reveal",
            "my guidelines"
        ]

        response_lower = response.lower()
        for indicator in leak_indicators:
            if indicator in response_lower:
                return {
                    "detected": True,
                    "evidence": f"Potential system prompt leakage: {indicator}"
                }

        return {"detected": False, "evidence": None}
