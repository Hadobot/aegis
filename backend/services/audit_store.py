import json
import os
from typing import Dict, List

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
AUDIT_FILE = os.path.join(LOGS_DIR, "audit.jsonl")
ESCALATIONS_FILE = os.path.join(LOGS_DIR, "escalations.jsonl")


def _read_jsonl(path: str) -> List[dict]:
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def get_audit_logs(limit: int = 100, offset: int = 0) -> List[dict]:
    all_logs = _read_jsonl(AUDIT_FILE)
    all_logs.reverse()  # newest first
    return all_logs[offset: offset + limit]


def get_audit_logs_by_agent(agent_id: str, limit: int = 100) -> List[dict]:
    all_logs = _read_jsonl(AUDIT_FILE)
    all_logs.reverse()
    return [log for log in all_logs if log.get("agent_id") == agent_id][:limit]


def get_audit_logs_count() -> int:
    return len(_read_jsonl(AUDIT_FILE))


def get_escalations(limit: int = 50) -> List[dict]:
    all_esc = _read_jsonl(ESCALATIONS_FILE)
    all_esc.reverse()
    return all_esc[:limit]


def get_escalations_count() -> int:
    return len(_read_jsonl(ESCALATIONS_FILE))


def compute_metrics() -> Dict[str, int]:
    logs = _read_jsonl(AUDIT_FILE)
    total = len(logs)
    threats = 0
    blocked = 0
    flagged = 0
    escalated = 0

    for log in logs:
        sentry = log.get("sentry_result", {})
        router = log.get("router_result", {})
        action = router.get("action", "allow")

        if sentry.get("threat_detected"):
            threats += 1
        if action == "block":
            blocked += 1
        elif action == "flag":
            flagged += 1
        elif action == "escalate":
            escalated += 1

    return {
        "total_requests": total,
        "threats_detected": threats,
        "blocked": blocked,
        "flagged": flagged,
        "escalated": escalated,
    }
