from fastmcp import FastMCP
from datetime import datetime
from typing import Dict, Any, List
import json
import os

mcp = FastMCP("audit-server")

AUDIT_LOG_FILE = "logs/audit.jsonl"


@mcp.tool()
async def audit_log_write(
    request_id: str,
    agent_id: str,
    action: str,
    threat_type: str,
    confidence: float,
    decision: str,
    compliance_refs: List[str],
    reasoning: str
) -> Dict[str, Any]:
    """Write structured audit entries with full trace context."""
    os.makedirs("logs", exist_ok=True)

    entry = {
        "log_id": f"audit-{request_id}",
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "agent_id": agent_id,
        "action": action,
        "threat_type": threat_type,
        "confidence": confidence,
        "decision": decision,
        "compliance_refs": compliance_refs,
        "reasoning": reasoning
    }

    with open(AUDIT_LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {
        "logged": True,
        "log_id": entry["log_id"],
        "timestamp": entry["timestamp"]
    }


@mcp.tool()
async def audit_log_read(request_id: str = None, limit: int = 100) -> Dict[str, Any]:
    """Read audit log entries."""
    if not os.path.exists(AUDIT_LOG_FILE):
        return {"entries": [], "total": 0}

    entries = []
    with open(AUDIT_LOG_FILE, "r") as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                if request_id and entry.get("request_id") != request_id:
                    continue
                entries.append(entry)

    return {
        "entries": entries[-limit:],
        "total": len(entries)
    }


if __name__ == "__main__":
    mcp.run()
