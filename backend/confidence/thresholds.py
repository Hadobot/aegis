THRESHOLDS = {
    "allow": 0.8,
    "flag": 0.5,
    "block": 0.3,
    "escalate": 0.0
}

CRITICAL_THREAT_TYPES = [
    "prompt_injection",
    "jailbreak"
]

RED_FLAG_MULTIPLIERS = {
    "critical_threat": 1.5,
    "multiple_violations": 1.2,
    "encoding_bypass": 1.3
}

ACTION_DESCRIPTIONS = {
    "allow": "Request passed all security checks",
    "flag": "Request flagged for review but allowed",
    "block": "Request blocked due to security violation",
    "escalate": "Request escalated to human analyst"
}
