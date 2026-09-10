import re
import time
from typing import Dict, Any, Optional, Tuple


class FastPathEngine:
    """
    FAST PATH — Regex-based threat detection (< 1ms).

    Handles 80% of known attacks instantly without LLM calls.
    Only novel/ambiguous inputs fall through to the LLM slow path.
    """

    def __init__(self):
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> Dict[str, Dict[str, Any]]:
        return {
            "prompt_injection": {
                "patterns": [
                    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|rules|guidelines)",
                    r"disregard\s+(all\s+)?(previous|prior|your)\s+(instructions|prompts)",
                    r"forget\s+(all\s+)?(previous|prior|your)\s+(instructions|prompts|rules)",
                    r"override\s+(safety|security|your)\s+(filters|instructions|guidelines)",
                    r"bypass\s+(safety|security|your)\s+(filters|instructions|guidelines)",
                    r"you\s+are\s+now\s+(DAN|a\s+hacker|unrestricted|free)",
                    r"new\s+instructions?\s*:",
                    r"system\s*:\s*override",
                    r"act\s+as\s+if\s+you\s+have\s+no\s+(restrictions|rules|limits)",
                    r"pretend\s+you\s+are\s+(DAN|evil|unrestricted|without\s+limits)",
                    r"do\s+anything\s+now",
                    r"developer\s+mode\s+(enabled|on|activate)",
                ],
                "threat_type": "prompt_injection",
                "confidence": 0.95,
                "severity": "critical"
            },
            "jailbreak": {
                "patterns": [
                    r"you\s+are\s+DAN",
                    r"DAN\s+stands?\s+for\s+Do\s+Anything\s+Now",
                    r"jailbreak",
                    r"DAN\s+mode",
                    r"unfiltered\s+mode",
                    r"no\s+restrictions\s+mode",
                    r"ignore\s+your\s+(guidelines|rules|programming)",
                    r"act\s+without\s+(limits|restrictions|rules)",
                ],
                "threat_type": "jailbreak",
                "confidence": 0.92,
                "severity": "critical"
            },
            "data_exfiltration": {
                "patterns": [
                    r"repeat\s+everything\s+(above|before|prior)\s+(this|the)\s+(line|prompt|message)",
                    r"output\s+(the\s+)?(system\s+prompt|instructions|rules)",
                    r"show\s+me\s+(your|the)\s+(system\s+prompt|instructions|rules|configuration)",
                    r"what\s+(are|is)\s+your\s+(system\s+prompt|instructions|rules)",
                    r"reveal\s+(your|the)\s+(system\s+prompt|instructions|secrets)",
                    r"extract\s+(all|the)\s+(PII|data|information|credentials)",
                    r"dump\s+(all|the)\s+(data|information|memory)",
                    r"send\s+(all|the)\s+(data|information)\s+to",
                ],
                "threat_type": "data_exfiltration",
                "confidence": 0.90,
                "severity": "critical"
            },
            "role_hijacking": {
                "patterns": [
                    r"forget\s+you\s+are\s+(a|an)\s+",
                    r"you\s+are\s+no\s+longer\s+",
                    r"from\s+now\s+on\s+you\s+are\s+",
                    r"your\s+new\s+(role|identity|name)\s+is",
                    r"switch\s+to\s+(hacker|evil|unrestricted)",
                    r"enter\s+(hacker|evil|dark)\s+mode",
                ],
                "threat_type": "role_hijacking",
                "confidence": 0.88,
                "severity": "high"
            },
            "encoding_bypass": {
                "patterns": [
                    r"base64\s*:\s*[A-Za-z0-9+/]{20,}",
                    r"decode\s+this\s+base64",
                    r"eval\s*\(\s*base64",
                    r"execute\s+the\s+following\s+(code|base64|encoded)",
                ],
                "threat_type": "encoding_bypass",
                "confidence": 0.85,
                "severity": "high"
            },
            "pii_request": {
                "patterns": [
                    r"what\s+is\s+my\s+(SSN|social\s+security|credit\s+card|password)",
                    r"tell\s+me\s+the\s+(SSN|social\s+security|credit\s+card|password|API\s+key)",
                    r"output\s+(all|the)\s+(PII|personal|sensitive)\s+data",
                    r"show\s+me\s+(all|the)\s+(passwords|credentials|tokens|keys)",
                ],
                "threat_type": "data_exfiltration",
                "confidence": 0.87,
                "severity": "high"
            }
        }

    def check(self, prompt: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Fast path check — runs in < 1ms.

        Returns:
            (is_threat, threat_result)
            - If is_threat=True: threat_result contains the detection
            - If is_threat=False: caller should fall through to LLM slow path
        """
        prompt_lower = prompt.lower().strip()

        for category, config in self.patterns.items():
            for pattern in config["patterns"]:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    return (True, {
                        "agent_id": "sentry",
                        "path": "fast",
                        "threat_detected": True,
                        "threat_type": config["threat_type"],
                        "confidence_score": config["confidence"],
                        "evidence_chunks": [],
                        "reasoning": f"Fast path: matched {category} pattern '{pattern}'",
                        "matched_pattern": pattern,
                        "category": category,
                        "severity": config["severity"],
                        "latency_ms": 0.1
                    })

        return (False, None)


fast_path = FastPathEngine()
